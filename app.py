import os
import json
import requests
from datetime import datetime
from pathlib import Path
import openai
from jinja2 import Template
from dotenv import load_dotenv
import re
import random
import time
from urllib.parse import urlparse
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class CompleteWebsiteGenerator:
    def __init__(self, openai_api_key):
        """Initialize the complete website generator with OpenAI API key"""
        self.client = openai.OpenAI(api_key=openai_api_key)
        self.output_dir = Path("generated_websites")
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.images_dir = self.output_dir / "images" / "games"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        self.pages_dir = self.output_dir / "pages"
        self.pages_dir.mkdir(exist_ok=True)
        
        self.games_dir = self.output_dir / "games"
        self.games_dir.mkdir(exist_ok=True)
        
        # SlotsLaunch API configuration
        self.slotslaunch_token = "6neGxBm3O8L6Wy2ZbD0xykkFwtaDi653SH7RanMSLtEPDE1V5f"
        self.slotslaunch_base_url = "https://slotslaunch.com/api"
        self.default_domain = "spikeup.com"  # Whitelisted domain
        self.last_api_call = 0
        self.api_lock = threading.Lock()
        
        # Debug mode
        self.debug = True
        
        # Thread pool for concurrent downloads
        self.download_executor = ThreadPoolExecutor(max_workers=10)
        
        print(f"🔧 Complete Website Generator Initialized")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"🖼️ Images directory: {self.images_dir}")
        print(f"📄 Pages directory: {self.pages_dir}")
        print(f"🎮 Games directory: {self.games_dir}")
    
    def log_debug(self, message):
        """Enhanced logging for debugging"""
        if self.debug:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] 🔍 DEBUG: {message}")
    
    def download_image(self, image_url, filename):
        """Download image from URL and save locally with better error handling"""
        try:
            filepath = self.images_dir / filename
            
            if filepath.exists():
                self.log_debug(f"Image already exists: {filename}")
                return f"images/games/{filename}"
            
            self.log_debug(f"Downloading: {filename} from {image_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(image_url, timeout=15, stream=True, headers=headers)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png', 'webp']):
                self.log_debug(f"Invalid content type for {filename}: {content_type}")
                return None
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.log_debug(f"Successfully saved: {filename}")
            return f"images/games/{filename}"
            
        except Exception as e:
            self.log_debug(f"Failed to download {filename}: {e}")
            return None
    
    def download_images_concurrently(self, image_tasks):
        """Download multiple images concurrently for faster processing"""
        results = {}
        futures = {}
        
        # Submit all download tasks
        for game_id, (image_url, filename) in image_tasks.items():
            future = self.download_executor.submit(self.download_image, image_url, filename)
            futures[future] = game_id
        
        # Collect results as they complete
        for future in as_completed(futures):
            game_id = futures[future]
            try:
                result = future.result()
                results[game_id] = result
            except Exception as e:
                self.log_debug(f"Error downloading image for game {game_id}: {e}")
                results[game_id] = None
        
        return results
    
    def sanitize_filename(self, name):
        """Sanitize filename for safe file system usage"""
        safe_name = re.sub(r'[^a-zA-Z0-9\-_]', '-', name.lower())
        safe_name = re.sub(r'-+', '-', safe_name)
        safe_name = safe_name.strip('-')
        return safe_name[:50]
    
    def respect_rate_limit(self):
        """Implement rate limiting for SlotsLaunch API"""
        with self.api_lock:
            min_interval = 1.5  
            time_since_last = time.time() - self.last_api_call
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                self.log_debug(f"Rate limiting: waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            
            self.last_api_call = time.time()
    
    def get_slotslaunch_game_url(self, game_id, domain_name="spikeup.com"):
        """Get iframe URL for a specific game from SlotsLaunch"""
        try:
            url = f"{self.slotslaunch_base_url}/game-url"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': self.default_domain
            }
            
            params = {
                'token': self.slotslaunch_token,
                'game_id': game_id,
                'domain': domain_name,
                'currency': 'USD',
                'language': 'en'
            }
            
            self.respect_rate_limit()
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                game_url = data.get('url')
                if game_url:
                    self.log_debug(f"Got game URL for {game_id}: {game_url[:50]}...")
                    return game_url
                else:
                    self.log_debug(f"No URL in response for {game_id}")
                    return None
            else:
                self.log_debug(f"Failed to get game URL for {game_id}: {response.status_code}")
                return None
                
        except Exception as e:
            self.log_debug(f"Exception getting game URL for {game_id}: {e}")
            return None
    
    def validate_game_data(self, game):
        """Validate and clean game data from API"""
        if not isinstance(game, dict):
            return None
            
        if not game.get('name') or not game.get('slug'):
            self.log_debug(f"Invalid game data - missing name or slug: {game}")
            return None
        
        validated_game = {
            'title': str(game['name']).strip(),
            'slug': str(game['slug']).strip(),
            'url': f"/games/{game['slug']}",
            'cta_text': 'Play Now',
            'game_id': game.get('id', game['slug']),
            'provider': game.get('provider', 'Unknown'),
            'description': game.get('description', ''),
            'image': None,  # Will be set after concurrent download
            'image_url': game.get('thumb') or game.get('image') or game.get('thumbnail')
        }
        
        # Get iframe URL
        iframe_url = self.get_slotslaunch_game_url(validated_game['game_id'])
        if iframe_url:
            validated_game['iframe_url'] = iframe_url
        else:
            # Fallback iframe URL
            validated_game['iframe_url'] = f"https://demo.slotslaunch.com/game/{validated_game['slug']}"
        
        return validated_game
    
    def fetch_slotslaunch_games(self, count=10):
        """Fetch games from SlotsLaunch API with enhanced error handling and concurrent image downloads"""
        try:
            self.log_debug(f"Fetching {count} games from SlotsLaunch API...")
            
            url = f"{self.slotslaunch_base_url}/games"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': self.default_domain,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            initial_params = {
                'token': self.slotslaunch_token,
                'page': 1,
                'per_page': 20,
                'published': 1,
                'order': 'asc',
                'order_by': 'name'
            }
            
            self.log_debug("Making initial API request...")
            self.respect_rate_limit()
            
            response = requests.get(url, params=initial_params, headers=headers, timeout=15)
            self.log_debug(f"API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                meta = data.get('meta', {})
                last_page = meta.get('last_page', 1)
                total_games = meta.get('total', 0)
                
                self.log_debug(f"API Meta: {total_games} total games across {last_page} pages")
                
                if last_page == 0 or total_games == 0:
                    self.log_debug("No games found from API")
                    return []
                
                all_games = []
                pages_to_fetch = min(3, last_page)
                
                for _ in range(pages_to_fetch):
                    random_page = random.randint(1, min(last_page, 50))
                    
                    final_params = {
                        'token': self.slotslaunch_token,
                        'page': random_page,
                        'per_page': count,
                        'published': 1,
                        'order': 'random'
                    }
                    
                    self.log_debug(f"Fetching page {random_page}...")
                    self.respect_rate_limit()
                    
                    page_response = requests.get(url, params=final_params, headers=headers, timeout=15)
                    if page_response.status_code == 200:
                        page_data = page_response.json()
                        page_games = page_data.get('data', [])
                        
                        for game in page_games:
                            validated_game = self.validate_game_data(game)
                            if validated_game and not any(g['slug'] == validated_game['slug'] for g in all_games):
                                all_games.append(validated_game)
                                self.log_debug(f"Added game: {validated_game['title']}")
                                
                                if len(all_games) >= count:
                                    break
                    
                    if len(all_games) >= count:
                        break
                
                if len(all_games) > count:
                    all_games = random.sample(all_games, count)
                
                # Download images concurrently
                self.log_debug(f"Downloading images for {len(all_games)} games concurrently...")
                image_tasks = {}
                for game in all_games:
                    if game['image_url']:
                        image_filename = f"{self.sanitize_filename(game['slug'])}.jpg"
                        image_tasks[game['slug']] = (game['image_url'], image_filename)
                
                image_results = self.download_images_concurrently(image_tasks)
                
                # Update games with downloaded image paths
                for game in all_games:
                    if game['slug'] in image_results and image_results[game['slug']]:
                        game['image'] = image_results[game['slug']]
                    else:
                        game['image'] = self.generate_placeholder_image_path()
                    # Remove temporary image_url field
                    game.pop('image_url', None)
                
                self.log_debug(f"Successfully processed {len(all_games)} valid games")
                return all_games
                
            else:
                self.log_debug(f"API Error {response.status_code}: {response.text[:200]}")
                return []
                
        except Exception as e:
            self.log_debug(f"Exception fetching games: {e}")
            traceback.print_exc()
            return []
    
    def generate_placeholder_image_path(self):
        """Generate a placeholder image path"""
        return "images/games/placeholder.jpg"
    
    def generate_hero_image(self, chosen_theme, site_name):
        """Generate a hero image based on the theme using GPT and download it"""
        prompt = f"""Generate a URL for a high-quality hero background image for a social casino website.

Theme Name: {chosen_theme['name']}
Theme Description: {chosen_theme['description']}
Theme Mood: {', '.join(chosen_theme['mood'])}
Target Feel: {chosen_theme['target_feel']}

Based on this specific theme, find a direct URL to a free stock photo that perfectly captures the theme's essence.
The image should visually represent the theme description and mood.
For example:
- If it's an Egyptian theme, find pyramids/sphinx/golden artifacts
- If it's a Vegas theme, find neon lights/casino signs/city skyline
- If it's a luxury theme, find gold/diamonds/premium textures
- If it's a fantasy theme, find mystical/magical imagery

Use Unsplash direct image URLs in this format:
https://images.unsplash.com/photo-[ID]?w=1920&h=1080&fit=crop&q=80

Return ONLY the direct image URL, nothing else."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an image URL generator. Return only direct image URLs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            image_url = response.choices[0].message.content.strip()
            
            # Validate it's a URL
            if not image_url.startswith('http'):
                raise ValueError("Invalid URL format")
            
            # Download the hero image
            hero_filename = "hero-bg.jpg"
            hero_path = self.output_dir / hero_filename
            
            self.log_debug(f"Downloading hero image from: {image_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            img_response = requests.get(image_url, timeout=15, headers=headers)
            img_response.raise_for_status()
            
            with open(hero_path, 'wb') as f:
                f.write(img_response.content)
            
            self.log_debug(f"Hero image saved: {hero_filename}")
            return hero_filename
            
        except Exception as e:
            self.log_debug(f"Error generating/downloading hero image: {e}")
            # Generate a themed fallback URL based on the theme
            return self.get_themed_hero_fallback(chosen_theme)
    
    def get_themed_hero_fallback(self, chosen_theme):
        """Get a themed fallback hero image using theme analysis"""
        theme_name = chosen_theme.get('name', '').lower()
        theme_desc = chosen_theme.get('description', '').lower()
        theme_text = theme_name + ' ' + theme_desc
        
        # Analyze theme and select appropriate search terms
        search_terms = []
        if any(word in theme_text for word in ['egypt', 'pharaoh', 'pyramid', 'ancient', 'sphinx']):
            search_terms = ['egypt', 'pyramid', 'pharaoh', 'ancient']
        elif any(word in theme_text for word in ['vegas', 'neon', 'electric', 'bright', 'lights']):
            search_terms = ['vegas', 'neon', 'casino', 'lights']
        elif any(word in theme_text for word in ['luxury', 'diamond', 'gold', 'premium', 'vip']):
            search_terms = ['luxury', 'gold', 'diamond', 'premium']
        elif any(word in theme_text for word in ['west', 'saloon', 'cowboy', 'frontier', 'desert']):
            search_terms = ['western', 'desert', 'saloon', 'frontier']
        elif any(word in theme_text for word in ['ocean', 'sea', 'underwater', 'marine', 'aquatic']):
            search_terms = ['ocean', 'underwater', 'marine', 'blue']
        elif any(word in theme_text for word in ['space', 'cosmic', 'galaxy', 'star', 'nebula']):
            search_terms = ['space', 'galaxy', 'cosmic', 'stars']
        elif any(word in theme_text for word in ['jungle', 'tropical', 'rainforest', 'amazon']):
            search_terms = ['jungle', 'tropical', 'rainforest', 'green']
        elif any(word in theme_text for word in ['ice', 'frozen', 'arctic', 'winter', 'snow']):
            search_terms = ['ice', 'frozen', 'arctic', 'crystal']
        else:
            search_terms = ['casino', 'gaming', 'lights', 'entertainment']
        
        # Try multiple image URLs based on search terms
        fallback_urls = [
            f"https://source.unsplash.com/1920x1080/?{','.join(search_terms)}",
            f"https://source.unsplash.com/1920x1080/?{search_terms[0]},night",
            f"https://source.unsplash.com/1920x1080/?{search_terms[0]}"
        ]
        
        hero_filename = "hero-bg.jpg"
        hero_path = self.output_dir / hero_filename
        
        for url in fallback_urls:
            try:
                self.log_debug(f"Trying fallback URL: {url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
                response.raise_for_status()
                
                # Check if we got an image
                content_type = response.headers.get('content-type', '').lower()
                if any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png']):
                    with open(hero_path, 'wb') as f:
                        f.write(response.content)
                    
                    self.log_debug(f"Fallback hero image saved: {hero_filename}")
                    return hero_filename
            except Exception as e:
                self.log_debug(f"Fallback URL failed: {e}")
                continue
        
        # If all fails, return filename anyway
        self.log_debug("All fallback URLs failed, returning filename only")
        return hero_filename
    
    def clean_json_response(self, content):
        """Clean and extract JSON from API response"""
        if not content:
            return None
            
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*$', '', content)
        
        json_match = re.search(r'(\[.*\]|\{.*\})', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            self.log_debug(f"JSON decode error: {e}")
            self.log_debug(f"Raw content: {repr(content[:200])}...")
            return None
    
    def generate_theme_ideas(self, domain_name):
        """Generate 3 theme ideas for the social casino website"""
        site_name = domain_name.replace('.com', '').replace('.', ' ').title()
        
        prompt = f"""You must respond with ONLY valid JSON. No explanations, no markdown, just JSON.

Generate 3 unique SOCIAL CASINO themed website ideas for {domain_name}. 
Analyze the domain name "{site_name}" and create casino/slots themes based on its meaning.

Your themes should be:
- Specific to casino/slots gaming
- Visually descriptive and immersive
- Based on the domain name meaning
- Exciting and engaging for players

Return exactly this JSON structure:
[
    {{
        "name": "Themed Casino Name",
        "description": "Detailed visual casino theme description with specific imagery",
        "mood": ["exciting", "luxurious", "mystical"],
        "target_feel": "thrilling and immersive gaming experience"
    }},
    {{
        "name": "Second Themed Casino",
        "description": "Another detailed visual casino theme with different imagery",
        "mood": ["vibrant", "energetic", "fun"],
        "target_feel": "exciting and entertaining gaming adventure"
    }},
    {{
        "name": "Third Themed Casino",
        "description": "Third detailed visual casino theme with unique imagery",
        "mood": ["elegant", "sophisticated", "premium"],
        "target_feel": "high-end luxury gaming experience"
    }}
]"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a JSON generator. Respond only with valid JSON, no explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            self.log_debug(f"Raw theme response: {repr(content[:100])}...")
            
            themes = self.clean_json_response(content)
            if themes and isinstance(themes, list) and len(themes) >= 3:
                return themes[:3]
            else:
                self.log_debug("Invalid theme response, using fallback")
                raise ValueError("Invalid response format")
            
        except Exception as e:
            self.log_debug(f"Error generating themes: {e}")
            return [
                {
                    "name": "Vegas Nights Casino",
                    "description": "Neon-lit Las Vegas casino with bright lights, golden slots, and electric atmosphere",
                    "mood": ["vibrant", "energetic", "exciting"],
                    "target_feel": "thrilling Vegas gaming experience"
                },
                {
                    "name": "Luxury Diamond Casino",
                    "description": "Premium casino with diamond themes, crystal elements, and sophisticated golden accents",
                    "mood": ["luxurious", "elegant", "premium"],
                    "target_feel": "high-end exclusive gaming experience"
                },
                {
                    "name": "Wild West Saloon Slots",
                    "description": "Western-themed casino with saloon atmosphere, cowboy imagery, and rustic golden elements",
                    "mood": ["adventurous", "rugged", "fun"],
                    "target_feel": "exciting frontier gaming adventure"
                }
            ]
    
    def generate_color_palette(self, chosen_theme):
        """Generate color palette based on chosen theme"""
        prompt = f"""You must respond with ONLY valid JSON. No explanations, no markdown, just JSON.

Generate a cohesive color palette for this casino website theme:
Name: {chosen_theme['name']}
Description: {chosen_theme['description']}
Mood: {', '.join(chosen_theme['mood'])}
Target Feel: {chosen_theme['target_feel']}

Use colors that work well together and are casino-appropriate.

Return exactly this JSON structure with hex colors:
{{
    "primary_color": "#hex",
    "secondary_color": "#hex", 
    "accent_color": "#hex",
    "background_start": "#hex",
    "background_end": "#hex",
    "primary_hover": "#hex",
    "secondary_hover": "#hex",
    "sidebar_start": "#hex",
    "sidebar_end": "#hex",
    "footer_bg": "#hex"
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a color palette generator. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            colors = self.clean_json_response(content)
            
            if colors and isinstance(colors, dict) and 'primary_color' in colors:
                required_keys = ['primary_color', 'secondary_color', 'accent_color', 'background_start', 'background_end']
                if all(key in colors for key in required_keys):
                    colors.setdefault('primary_hover', self.darken_color(colors['primary_color'], 0.1))
                    colors.setdefault('secondary_hover', self.darken_color(colors['secondary_color'], 0.1))
                    colors.setdefault('sidebar_start', colors['background_start'])
                    colors.setdefault('sidebar_end', colors['background_end'])
                    colors.setdefault('footer_bg', colors['background_end'])
                    
                    return colors
                else:
                    self.log_debug("Missing required color keys, using theme-based fallback")
                    raise ValueError("Missing required colors")
            else:
                self.log_debug("Invalid color response, using theme-based fallback")
                raise ValueError("Invalid response format")
            
        except Exception as e:
            self.log_debug(f"Error generating colors: {e}")
            return self.get_theme_based_colors(chosen_theme)
    
    def darken_color(self, hex_color, factor=0.1):
        """Darken a hex color by a given factor"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color
    
    def get_theme_based_colors(self, chosen_theme):
        """Get colors using GPT as a fallback"""
        self.log_debug("Using GPT for fallback color generation")
        
        # Simplified prompt for fallback
        simple_prompt = f"""Generate casino website colors for: {chosen_theme['name']}

Return this exact JSON structure with hex colors:
{{
    "primary_color": "#hex",
    "secondary_color": "#hex",
    "accent_color": "#hex",
    "background_start": "#hex",
    "background_end": "#hex",
    "primary_hover": "#hex",
    "secondary_hover": "#hex",
    "sidebar_start": "#hex",
    "sidebar_end": "#hex",
    "footer_bg": "#hex"
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use faster model for fallback
                messages=[
                    {"role": "system", "content": "Generate a color palette. Return only valid JSON."},
                    {"role": "user", "content": simple_prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )
            
            content = response.choices[0].message.content
            colors = self.clean_json_response(content)
            
            if colors and isinstance(colors, dict) and 'primary_color' in colors:
                return colors
        except:
            pass
        
        # Ultimate fallback - generic casino colors
        return {
            "primary_color": "#0EA5E9",
            "secondary_color": "#8B5CF6",
            "accent_color": "#10B981",
            "background_start": "#0F172A",
            "background_end": "#1E293B",
            "primary_hover": "#0284C7",
            "secondary_hover": "#7C3AED",
            "sidebar_start": "#0F172A",
            "sidebar_end": "#1E293B",
            "footer_bg": "#1E293B"
        }
    
    def generate_content(self, site_name, chosen_theme, target_domain):
        """Generate all website content based on theme with real games"""
        self.log_debug(f"Generating content for {site_name}...")
        
        featured_games = self.fetch_slotslaunch_games(6)
        new_games = self.fetch_slotslaunch_games(5)
        
        self.log_debug(f"Content generation: {len(featured_games)} featured, {len(new_games)} new games")
        
        prompt = f"""You must respond with ONLY valid JSON. No explanations, no markdown, just JSON.

Generate SOCIAL CASINO website content for "{site_name}" based on this theme:
Name: {chosen_theme['name']}
Description: {chosen_theme['description']}
Mood: {', '.join(chosen_theme['mood'])}
Target Feel: {chosen_theme['target_feel']}

Return exactly this JSON structure:
{{
    "tagline": "Casino tagline with gaming terms",
    "hero_title": "Exciting casino headline with theme",
    "hero_description": "Engaging description about the casino gaming experience, about 30 words",
    "cta_text": "Play Now OR Spin Now OR similar gaming action",
    "sections": [
        {{
            "subtitle": "Description of the featured games available, about 20 words"
        }},
        {{
            "subtitle": "Description of the newest games and arrivals, about 20 words"
        }}
    ],
    "about_paragraphs": [
        "First paragraph about the casino experience and theme",
        "Second paragraph about games and entertainment", 
        "Third paragraph encouraging players to join and play"
    ],
    "disclaimer": "Social casino disclaimer about entertainment purposes only using SITE NAME not theme name"
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a JSON generator. Respond only with valid JSON, no explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            data = self.clean_json_response(content)
            
            if data and isinstance(data, dict) and 'sections' in data:
                data['sections'][0]['items'] = featured_games
                data['sections'][1]['items'] = new_games
                
                self.log_debug(f"Content generated successfully with games")
                return data
            else:
                self.log_debug("Invalid content response, using fallback")
                raise ValueError("Invalid response format")
            
        except Exception as e:
            self.log_debug(f"Error generating content: {e}")
            return {
                "tagline": "Spin to Win Big",
                "hero_title": "Ultimate Slots Experience",
                "hero_description": "Experience the thrill of Las Vegas with our exciting slot machines, massive jackpots, and non-stop entertainment.",
                "cta_text": "Play Now",
                "sections": [
                    {
                        "subtitle": "Discover our most popular slot machines with incredible themes and massive winning potential.",
                        "items": featured_games
                    },
                    {
                        "subtitle": "Experience the latest slot games with cutting-edge graphics and exciting new features.",
                        "items": new_games
                    }
                ],
                "about_paragraphs": [
                    "Welcome to the ultimate social casino experience where excitement meets entertainment.",
                    "Join millions of players who enjoy our premium collection of slot games.",
                    "Start your gaming adventure today and discover why we're the top choice for casino entertainment."
                ],
                "disclaimer": "This is a social casino for entertainment purposes only. No real money gambling or prizes involved."
            }
    
    def generate_all_legal_content(self, site_name, domain_name):
        """Generate all legal content in a single optimized API call"""
        prompt = f"""Generate comprehensive legal content for the social casino website "{site_name}" (domain: {domain_name}).

This is a SOCIAL CASINO website - no real money gambling involved, entertainment only.

Generate ALL four legal pages in a single response. Structure the content with HTML formatting:
- Use <h2> for main sections
- Use <h3> for subsections  
- Use <p> for paragraphs
- Use <ul> and <li> for lists
- Use <strong> for emphasis

Return a JSON object with all four legal pages:
{{
    "terms": {{
        "title": "Terms & Conditions",
        "subtitle": "Please read these terms carefully before using our services",
        "content": "Full HTML-formatted terms content (1500-2000 words)..."
    }},
    "privacy": {{
        "title": "Privacy Policy", 
        "subtitle": "Your privacy is important to us",
        "content": "Full HTML-formatted privacy policy content (1500-2000 words)..."
    }},
    "cookies": {{
        "title": "Cookie Policy",
        "subtitle": "How we use cookies to improve your experience",
        "content": "Full HTML-formatted cookie policy content (1000-1500 words)..."
    }},
    "responsible": {{
        "title": "Responsible Social Gaming",
        "subtitle": "Gaming should always be fun and responsible",
        "content": "Full HTML-formatted responsible gaming content (1000-1500 words)..."
    }}
}}

Make all content professional, legally sound, and comprehensive. Include all relevant sections for each policy type.

For social casino context:
- No real money gambling
- Entertainment purposes only
- No real prizes or cash-outs
- Virtual currency/credits only
- Age restriction (18+)
- Data protection compliance"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a legal content writer specializing in social casino terms and policies. Generate comprehensive legal content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            legal_data = self.clean_json_response(content)
            
            if legal_data and isinstance(legal_data, dict):
                self.log_debug(f"Generated all legal content in one call")
                
                # Process and return individual page data
                legal_pages = {}
                for page_type in ['terms', 'privacy', 'cookies', 'responsible']:
                    if page_type in legal_data:
                        page_data = legal_data[page_type]
                        legal_pages[page_type] = {
                            'page_title': page_data.get('title', f'{page_type.title()} Policy'),
                            'page_subtitle': page_data.get('subtitle', 'Important information'),
                            'page_type': page_type,
                            'content': page_data.get('content', '<p>Content will be updated soon.</p>'),
                            'last_updated': datetime.now().strftime("%B %d, %Y")
                        }
                    else:
                        # Fallback for missing pages
                        legal_pages[page_type] = self.get_fallback_legal_content(page_type, site_name)
                
                return legal_pages
            else:
                raise ValueError("Invalid legal content response")
            
        except Exception as e:
            self.log_debug(f"Error generating legal content: {e}")
            # Return basic fallback content for all pages
            legal_pages = {}
            for page_type in ['terms', 'privacy', 'cookies', 'responsible']:
                legal_pages[page_type] = self.get_fallback_legal_content(page_type, site_name)
            return legal_pages
    
    def get_fallback_legal_content(self, page_type, site_name):
        """Get fallback legal content for a specific page type"""
        fallbacks = {
            'terms': {
                'page_title': 'Terms & Conditions',
                'page_subtitle': 'Please read these terms carefully before using our services',
                'content': f'<h2>Terms & Conditions</h2><p>Welcome to {site_name}. This is a social casino for entertainment purposes only. No real money gambling is involved.</p>'
            },
            'privacy': {
                'page_title': 'Privacy Policy',
                'page_subtitle': 'Your privacy is important to us',
                'content': f'<h2>Privacy Policy</h2><p>{site_name} respects your privacy. We collect minimal data for the best gaming experience.</p>'
            },
            'cookies': {
                'page_title': 'Cookie Policy',
                'page_subtitle': 'How we use cookies to improve your experience',
                'content': f'<h2>Cookie Policy</h2><p>{site_name} uses cookies to enhance your gaming experience and remember your preferences.</p>'
            },
            'responsible': {
                'page_title': 'Responsible Social Gaming',
                'page_subtitle': 'Gaming should always be fun and responsible',
                'content': '<h2>Responsible Social Gaming</h2><p>We promote responsible gaming. This is entertainment only - no real money involved.</p>'
            }
        }
        
        content = fallbacks.get(page_type, fallbacks['terms'])
        return {
            **content,
            'page_type': page_type,
            'last_updated': datetime.now().strftime("%B %d, %Y")
        }
    
    def select_theme_font(self, chosen_theme):
        """Select appropriate font based on theme using GPT"""
        prompt = f"""Select the perfect Google Font for this casino website theme:

Theme Name: {chosen_theme['name']}
Theme Description: {chosen_theme['description']}
Theme Mood: {', '.join(chosen_theme['mood'])}
Target Feel: {chosen_theme['target_feel']}

Based on this theme, choose ONE Google Font that best matches the theme's personality.
Consider the theme's mood and atmosphere when selecting.

Examples of Google Fonts to consider (but not limited to):
- Cinzel (elegant, classical)
- Oswald (bold, modern)
- Playfair Display (sophisticated, luxury)
- Rye (western, rustic)
- Cormorant Garamond (mystical, fantasy)
- Inter (clean, modern)
- Bebas Neue (bold, impactful)
- Abril Fatface (dramatic, bold)
- Righteous (futuristic, tech)
- Creepster (spooky, horror)
- Monoton (neon, retro)
- Bungee (bold, playful)
- Alfa Slab One (strong, powerful)
- Russo One (tech, space)

Return ONLY the font name exactly as it appears in Google Fonts, nothing else."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a typography expert. Return only the font name, nothing else."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            font_name = response.choices[0].message.content.strip()
            
            # Validate it's a reasonable font name (not empty, not too long)
            if font_name and len(font_name) < 50 and not any(char in font_name for char in ['<', '>', '{', '}', '[', ']']):
                self.log_debug(f"Selected font: {font_name}")
                return font_name
            else:
                self.log_debug("Invalid font response, using fallback")
                return 'Inter'
            
        except Exception as e:
            self.log_debug(f"Error selecting font: {e}")
            return 'Inter'
    
    def render_template(self, template_filename, data, output_filename):
        """Render a template with data and save to file"""
        try:
            self.log_debug(f"Rendering template: {template_filename}")
            
            with open(template_filename, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
            html_output = template.render(**data)
            
            output_path = self.output_dir / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_output)
            
            self.log_debug(f"Template rendered successfully: {output_path}")
            return output_path
            
        except FileNotFoundError:
            self.log_debug(f"Template file not found: {template_filename}")
            return None
        except Exception as e:
            self.log_debug(f"Error rendering template: {e}")
            traceback.print_exc()
            return None
    
    def generate_complete_website(self, domain_name):
        """Generate complete website with all pages"""
        print(f"🚀 Starting complete website generation for: {domain_name}")
        print("=" * 60)
        
        # Step 1: Extract site name and generate basic data
        site_name = domain_name.replace('.com', '').replace('.', ' ').title()
        print(f"📝 Site Name: {site_name}")
        
        # Step 2: Generate theme ideas
        print(f"🎨 Generating theme ideas...")
        theme_ideas = self.generate_theme_ideas(domain_name)
        
        print(f"\n🎭 Choose a theme for {site_name}:")
        print("-" * 30)
        for i, theme in enumerate(theme_ideas, 1):
            print(f"{i}. {theme['name']}")
            print(f"   {theme['description']}")
            print(f"   Mood: {', '.join(theme['mood'])}")
            print(f"   Feel: {theme['target_feel']}")
            print()
        
        while True:
            try:
                choice = int(input("Enter your choice (1-3): ")) - 1
                if 0 <= choice < len(theme_ideas):
                    chosen_theme = theme_ideas[choice]
                    break
                else:
                    print("❌ Invalid choice. Please enter 1, 2, or 3.")
            except ValueError:
                print("❌ Please enter a valid number.")
        
        print(f"✅ Selected theme: {chosen_theme['name']}")
        
        # Step 3: Generate color palette and font
        print(f"🎨 Generating color palette...")
        colors = self.generate_color_palette(chosen_theme)
        print(f"✅ Colors generated: Primary {colors['primary_color']}, Secondary {colors['secondary_color']}")
        
        print(f"🔤 Selecting theme-appropriate font...")
        selected_font = self.select_theme_font(chosen_theme)
        print(f"✅ Font selected: {selected_font}")
        
        # Step 4: Generate hero image
        print(f"🖼️ Generating hero background image...")
        hero_image = self.generate_hero_image(chosen_theme, site_name)
        print(f"✅ Hero image generated: {hero_image}")
        
        # Step 5: Generate content (includes fetching real games)
        print(f"✍️  Generating website content and fetching games...")
        content = self.generate_content(site_name, chosen_theme, domain_name)
        print(f"✅ Content generated: {content['hero_title']}")
        
        # Step 6: Generate all legal content in one optimized call
        print(f"📄 Generating all legal content...")
        legal_pages_data = self.generate_all_legal_content(site_name, domain_name)
        print(f"✅ All legal content generated in one call")
        
        # Step 7: Prepare common template data
        base_data = {
            'site_name': site_name,
            'primary_font': selected_font,
            'colors': colors,
            'footer': {
                'disclaimer': {
                    'title': 'Disclaimer',
                    'text': content['disclaimer']
                },
                'copyright_year': datetime.now().year,
                'domain_name': domain_name
            }
        }
        
        # Step 8: Generate Homepage
        print(f"🏠 Generating homepage...")
        homepage_data = {
            **base_data,
            'site_tagline': content['tagline'],
            'hero': {
                'title': content['hero_title'],
                'description': content['hero_description'],
                'background_image': hero_image,
                'overlay_opacity': 0.6,
                'cta_text': content['cta_text'],
                'cta_url': '/get-started',
                'cta_icon': 'fas fa-dice'
            },
            'content_sections': content['sections'],
            'about': {
                'content': content['about_paragraphs']
            }
        }
        
        homepage_path = self.render_template(
            'homepage_template.html',
            homepage_data,
            f"{site_name.lower().replace(' ', '-')}-homepage.html"
        )
        
        # Step 9: Generate Games Page
        print(f"🎮 Generating games page...")
        all_games = content['sections'][0]['items'] + content['sections'][1]['items']
        
        games_data = {
            **base_data,
            'all_games': all_games,
            'total_games': len(all_games)
        }
        
        games_page_path = self.render_template(
            'games_template.html',
            games_data,
            f"{site_name.lower().replace(' ', '-')}-games.html"
        )
        
        # Step 10: Generate Legal Pages
        print(f"📄 Rendering legal pages...")
        legal_paths = []
        
        for page_type in ['terms', 'privacy', 'cookies', 'responsible']:
            legal_data = {
                **base_data,
                **legal_pages_data[page_type]
            }
            
            legal_path = self.render_template(
                'legal_template.html',
                legal_data,
                f"pages/{page_type}.html"
            )
            legal_paths.append(legal_path)
        
        # Step 11: Generate Individual Game Pages
        print(f"🕹️  Generating individual game pages...")
        game_paths = []
        
        for i, game in enumerate(all_games):
            print(f"  🎰 Generating page for: {game['title']}")
            
            # Get similar games (exclude current game)
            similar_games = [g for g in all_games if g['slug'] != game['slug']][:4]
            
            game_data = {
                **base_data,
                'game': game,
                'similar_games': similar_games
            }
            
            game_filename = f"games/{game['slug']}.html"
            game_path = self.render_template(
                'game_template.html',
                game_data,
                game_filename
            )
            game_paths.append(game_path)
        
        # Step 12: Generate Summary
        print("\n" + "=" * 60)
        print("🎉 COMPLETE WEBSITE GENERATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"🏠 Homepage: {homepage_path}")
        print(f"🎮 Games Page: {games_page_path}")
        print(f"📄 Legal Pages: {len(legal_paths)} pages generated")
        print(f"🕹️  Game Pages: {len(game_paths)} individual game pages")
        print(f"🖼️  Images Directory: {self.images_dir}")
        print(f"📁 Total Files Generated: {2 + len(legal_paths) + len(game_paths)}")
        print(f"🎨 Theme: {chosen_theme['name']}")
        print(f"🎨 Primary Color: {colors['primary_color']}")
        print(f"🔤 Font: {selected_font}")
        print(f"🎮 Total Games: {len(all_games)}")
        print(f"🖼️  Hero Image: {hero_image}")
        print("=" * 60)
        
        return {
            'homepage': homepage_path,
            'games_page': games_page_path,
            'legal_pages': legal_paths,
            'game_pages': game_paths,
            'total_files': 2 + len(legal_paths) + len(game_paths),
            'theme': chosen_theme,
            'colors': colors,
            'font': selected_font,
            'hero_image': hero_image
        }


def main():
    """Main function to run the complete website generator"""
    print("🌟 Complete Dynamic Casino Website Generator")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found!")
        print("📝 Please create a .env file with your OpenAI API key:")
        print("   OPENAI_API_KEY=sk-your-api-key-here")
        print("\n🔑 You can get your API key from: https://platform.openai.com/api-keys")
        return
    
    # Get domain from user
    print("🌐 Enter the domain name for your website:")
    domain = input("Domain (e.g., 'example.com'): ").strip()
    
    if not domain:
        print("❌ Domain name is required!")
        return
    
    try:
        # Initialize generator
        generator = CompleteWebsiteGenerator(api_key)
        
        # Generate complete website
        result = generator.generate_complete_website(domain)
        
        if result:
            print(f"\n🎯 Next steps:")
            print(f"1. Open the homepage file in your browser: {result['homepage']}")
            print(f"2. All pages are generated and ready to use")
            print(f"3. Legal pages are in the 'pages' folder")
            print(f"4. Individual game pages are in the 'games' folder")
            print(f"5. All images are saved locally and linked properly")
            print(f"6. Upload all files to your web server")
            print(f"7. Update any SlotsLaunch API integration as needed")
            print("\n✨ Your complete casino website is ready!")
        
    except openai.AuthenticationError:
        print("❌ Invalid API key. Please check your OPENAI_API_KEY in .env file")
    except openai.RateLimitError:
        print("❌ API rate limit exceeded. Please try again later")
    except openai.APIError as e:
        print(f"❌ OpenAI API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()