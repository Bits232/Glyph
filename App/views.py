import json
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from groq import Groq
from dotenv import load_dotenv
import requests
import base64
import time
from django.contrib.sessions.models import Session
from django.core.files.storage import default_storage
from supabase import create_client, Client

load_dotenv()
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
# Test user credentials
TEST_USER_EMAIL = "test@glyph.com"
TEST_USER_PASSWORD = "GlyphTest2026"

def login_page(request):
    """Render login page"""
    return render(request, 'App/login.html')

@csrf_exempt
def login_user(request):
    """Handle login"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()
            password = data.get('password', '').strip()
            
            if email == TEST_USER_EMAIL.lower() and password == TEST_USER_PASSWORD:
                response = JsonResponse({
                    'success': True,
                    'redirect': '/editor/'
                })
                # Set simple auth cookie
                response.set_cookie('glyph_auth', 'yes', max_age=86400, httponly=True,secure=True,samesite='Lax')
                return response
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Not commercially available yet. Join the waitlist!'
                })
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def logout_user(request):
    """Handle logout"""
    response = redirect('/login/')
    response.delete_cookie('glyph_auth')
    return response

def editor_ui(request):
    """Show editor - check auth cookie"""
    if not request.COOKIES.get('glyph_auth'):
        return redirect('/login/')
    
    context = {
        'user_email': 'test@glyph.com',
        'user_name': 'Test User'
    }
    return render(request, 'App/editor_ui.html', context)


@csrf_exempt
def ai_request(request):
    
    """
    Handle AI requests for Edit, Generate, Ask
    Also handles OPTIONS preflight requests
    """
    # Handle OPTIONS preflight (from browser)
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    # Handle POST requests
    if request.method == 'POST':
        try:
            # Parse request
            data = json.loads(request.body)
            action = data.get('action')
            user_text = data.get('text', '').strip()
            context = data.get('context', '').strip()
            word_range = data.get('word_range', '')
            
            # Validate
            if not action or action not in ['edit', 'generate', 'ask']:
                return JsonResponse({'error': 'Invalid action. Use edit, generate, or ask.'}, status=400)
            
            if not user_text:
                return JsonResponse({'error': 'No input provided'}, status=400)
            
            # Get API key
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                return JsonResponse({'error': 'API key not configured in .env'}, status=500)
            
            # Prepare prompt based on action
            prompt = prepare_prompt(action, user_text, context, word_range)
            
            # Call Groq
            client = Groq(api_key=api_key)
            
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000,
            )
            
            result = response.choices[0].message.content
             # LOG TO SUPABASE
            try:
                supabase.table('ai_logs').insert({
                    'action': action,
                    'user_input': user_text[:500],  # Truncate to avoid huge logs
                    'response_text': result[:500],
                    'tokens_used': response.usage.total_tokens,
                    'user_email': request.session.get('user_email', 'anonymous'),
                    'context_length': len(context)
                }).execute()
            except Exception as log_error:
                print(f"Logging error: {log_error}")  # Don't break app if logging fails    
            # Add CORS headers to response
            json_response = JsonResponse({
                'success': True,
                'action': action,
                'result': result,
                'tokens_used': response.usage.total_tokens
            })
            json_response['Access-Control-Allow-Origin'] = '*'
            return json_response
            
        except json.JSONDecodeError:
            error_response = JsonResponse({'error': 'Invalid JSON in request'}, status=400)
            error_response['Access-Control-Allow-Origin'] = '*'
            return error_response
        except Exception as e:
             # LOG ERROR TO SUPABASE
            try:
                supabase.table('ai_logs').insert({
                    'action': 'ERROR',
                    'user_input': str(e),
                    'response_text': 'Error occurred',
                    'tokens_used': 0,
                    'user_email': request.session.get('user_email', 'anonymous'),
                    'context_length': 0
                }).execute()
            except:
                pass
            error_response = JsonResponse({'error': f'AI Service Error: {str(e)}'}, status=500)
            error_response['Access-Control-Allow-Origin'] = '*'
            return error_response
    
    # Handle other methods
    error_response = JsonResponse({'error': 'Method not allowed'}, status=405)
    error_response['Access-Control-Allow-Origin'] = '*'
    return error_response

@csrf_exempt

def video_to_text(request):
    
    """
    Handle video URL and transcription using Mux API
    """
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    if request.method == 'POST':
        try:
            # Parse JSON request
            data = json.loads(request.body)
            video_url = data.get('video_url', '').strip()
            
            if not video_url:
                return JsonResponse({'error': 'No video URL provided'}, status=400)
            # LOG VIDEO REQUEST START
            try:
                supabase.table('video_logs').insert({
                    'video_url': video_url,
                    'transcript_length': 0,
                    'status': 'processing'
                }).execute()
            except:
                pass
            # Check Mux credentials
            mux_token_id = os.getenv('MUX_TOKEN_ID')
            mux_token_secret = os.getenv('MUX_TOKEN_SECRET')
            
            if not mux_token_id or not mux_token_secret:
                return JsonResponse({'error': 'Mux credentials not configured in .env'}, status=500)
            
            # Create Basic Auth header
            credentials = f"{mux_token_id}:{mux_token_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json'
            }
            
            # Create Mux asset with auto-generated captions
            create_payload = {
                "input": [
                    {
                        "url": video_url,
                        "generated_subtitles": [
                            {
                                "language_code": "en",
                                "name": "English CC"
                            }
                        ]
                    }
                ],
                "playback_policy": ["public"]
            }
            
            # POST to Mux API
            create_response = requests.post(
                'https://api.mux.com/video/v1/assets',
                headers=headers,
                json=create_payload
            )
            
            if create_response.status_code != 201:
                return JsonResponse({
                    'error': f'Mux API error: {create_response.text}'
                }, status=500)
            
            asset_data = create_response.json()
            asset_id = asset_data['data']['id']
            
            # Wait for asset to be ready and captions to be generated
            max_wait = 600  # 10 minutes max
            wait_time = 0
            track_id = None
            playback_id = None
            
            while wait_time < max_wait:
                time.sleep(15)  # Check every 15 seconds
                wait_time += 15
                
                # Get asset status
                asset_response = requests.get(
                    f'https://api.mux.com/video/v1/assets/{asset_id}',
                    headers=headers
                )
                
                if asset_response.status_code != 200:
                    continue
                
                asset_info = asset_response.json()
                
                # Get playback ID
                if not playback_id and asset_info['data'].get('playback_ids'):
                    playback_id = asset_info['data']['playback_ids'][0]['id']
                
                # Check if there's a generated text track ready
                if asset_info['data'].get('tracks'):
                    for track in asset_info['data']['tracks']:
                        if (track.get('type') == 'text' and 
                            track.get('text_source') == 'generated_vod' and
                            track.get('status') == 'ready'):
                            track_id = track['id']
                            break
                
                if track_id and playback_id:
                    break
            
            if not track_id or not playback_id:
                return JsonResponse({
                    'error': 'Caption generation timed out or failed'
                }, status=500)
            
            # Fetch transcript from Mux CDN
            transcript_url = f"https://stream.mux.com/{playback_id}/text/{track_id}.txt"
            
            transcript_response = requests.get(transcript_url)
            
            if transcript_response.status_code != 200:
                return JsonResponse({
                    'error': f'Failed to fetch transcript: {transcript_response.text}'
                }, status=500)
            
            transcript = transcript_response.text
            # LOG SUCCESS
            try:
                supabase.table('video_logs').insert({
                    'video_url': video_url,
                    'transcript_length': len(transcript),
                    'status': 'success'
                }).execute()
            except:
                pass
            # Return transcript
            json_response = JsonResponse({
                'success': True,
                'transcript': transcript,
                'asset_id': asset_id
            })
            json_response['Access-Control-Allow-Origin'] = '*'
            return json_response
            
        except Exception as e:
            # LOG ERROR
            try:
                supabase.table('video_logs').insert({
                    'video_url': video_url if 'video_url' in locals() else 'unknown',
                    'transcript_length': 0,
                    'status': 'error',
                    'error_message': str(e)
                }).execute()
            except:
                pass
            error_response = JsonResponse({
                'error': f'Video processing error: {str(e)}'
            }, status=500)
            error_response['Access-Control-Allow-Origin'] = '*'
            return error_response
    
    error_response = JsonResponse({'error': 'Method not allowed'}, status=405)
    error_response['Access-Control-Allow-Origin'] = '*'
    return error_response
def prepare_prompt(action, user_text, context, word_range):
    """Create appropriate prompt for each action"""
    
    if action == 'edit':
        if context:
            return f"""You are a text editor. Edit the following text based on the user's instruction.

TEXT TO EDIT:
{context}

USER INSTRUCTION: {user_text}

Return ONLY the edited text in HTML format. Use HTML tags like <p>, <h1>, <h2>, <strong>, <em>, <ul>, <li>, etc.
Do NOT include any explanations, notes, or the original instruction in your response.
Just return the edited HTML content directly.

EDITED TEXT:"""
        else:
            return f"""You are a text editor. Edit this based on the instruction: {user_text}

Return ONLY the edited text in HTML format. No explanations."""
    
    elif action == 'generate':
        return f"""Generate content based on this request: {user_text}

Return the content in HTML format using tags like <h1>, <h2>, <p>, <strong>, <em>, <ul>, <ol>, <li>.
Return ONLY the HTML content, no explanations."""
    
    elif action == 'ask':
        if context:
            return f"""Answer this question based on the provided text.

TEXT:
{context}

QUESTION: {user_text}

Provide a clear, direct answer. If the text doesn't contain the information, say so."""
        else:
            return f"""Answer this question: {user_text}

Provide a helpful, accurate answer."""
    
    return user_text