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

class DynamicWebsiteGenerator:
    def __init__(self, openai_api_key):
        """Initialize the website generator with OpenAI API key"""
        self.client = openai.OpenAI(api_key=openai_api_key)
        self.output_dir = Path("generated_websites")
        self.output_dir.mkdir(exist_ok=True)
        
        # Create images directory
        self.images_dir = self.output_dir / "images" / "games"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # CORRECT SlotsLaunch API configuration
        self.slotslaunch_token = "6neGxBm3O8L6Wy2ZbD0xykkFwtaDi653SH7RanMSLtEPDE1V5f"
        self.slotslaunch_base_url = "https://slotslaunch.com/api"
        self.default_domain = "spikeup.com"  # ALWAYS use this as Origin - it's whitelisted
        self.last_api_call = 0  # For rate limiting (SlotsLaunch: 2 r/s premium, 0.5 r/s free)
        
        # Debug mode for better troubleshooting
        self.debug = True
        
        print(f"🔧 Initialized with SlotsLaunch API token: {self.slotslaunch_token[:10]}...")
        print(f"📍 Using whitelisted domain: {self.default_domain}")
        print(f"📁 Images will be saved to: {self.images_dir}")
    
    def log_debug(self, message):
        """Enhanced logging for debugging"""
        if self.debug:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] 🔍 DEBUG: {message}")
    
    def download_image(self, image_url, filename):
        """Download image from URL and save locally with better error handling"""
        try:
            # Create full path
            filepath = self.images_dir / filename
            
            # Skip if already exists
            if filepath.exists():
                self.log_debug(f"Image already exists: {filename}")
                return f"images/games/{filename}"
            
            self.log_debug(f"Downloading: {filename} from {image_url}")
            
            # Add headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(image_url, timeout=15, stream=True, headers=headers)
            response.raise_for_status()
            
            # Check if response is actually an image
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png', 'webp']):
                self.log_debug(f"Invalid content type for {filename}: {content_type}")
                return self.get_fallback_image_path(filename)
            
            # Save image
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.log_debug(f"Successfully saved: {filename}")
            return f"images/games/{filename}"
            
        except Exception as e:
            self.log_debug(f"Failed to download {filename}: {e}")
            return self.get_fallback_image_path(filename)
    
    def get_fallback_image_path(self, filename):
        """Generate fallback image path for failed downloads"""
        # Create a simple placeholder image path or use a default
        return f"images/games/placeholder.jpg"
    
    def sanitize_filename(self, name):
        """Sanitize filename for safe file system usage"""
        # Remove special characters and replace spaces
        safe_name = re.sub(r'[^a-zA-Z0-9\-_]', '-', name.lower())
        # Remove multiple dashes
        safe_name = re.sub(r'-+', '-', safe_name)
        # Remove leading/trailing dashes
        safe_name = safe_name.strip('-')
        return safe_name[:50]  # Limit length
    
    def respect_rate_limit(self):
        """Implement rate limiting for SlotsLaunch API"""
        # Conservative rate limiting: 1 request per 1.5 seconds
        min_interval = 1.5  
        time_since_last = time.time() - self.last_api_call
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            self.log_debug(f"Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        
        self.last_api_call = time.time()
    
    def validate_game_data(self, game):
        """Validate and clean game data from API"""
        if not isinstance(game, dict):
            return None
            
        # Required fields
        if not game.get('name') or not game.get('slug'):
            self.log_debug(f"Invalid game data - missing name or slug: {game}")
            return None
        
        # Clean and validate data
        validated_game = {
            'title': str(game['name']).strip(),
            'slug': str(game['slug']).strip(),
            'url': f"/games/{game['slug']}",
            'cta_text': 'Play Now',
            'game_id': game.get('id', game['slug']),
            'provider': game.get('provider', 'Unknown')
        }
        
        # Handle image
        image_url = game.get('thumb') or game.get('image') or game.get('thumbnail')
        if image_url:
            image_filename = f"{self.sanitize_filename(game['slug'])}.jpg"
            local_image_path = self.download_image(image_url, image_filename)
            validated_game['image'] = local_image_path
        else:
            validated_game['image'] = self.generate_fallback_image_url(validated_game['title'])
        
        return validated_game
    
    def fetch_slotslaunch_games(self, count=10, domain_name="spikeup.com"):
        """Fetch games from SlotsLaunch API with enhanced error handling"""
        try:
            self.log_debug(f"Fetching {count} games from SlotsLaunch API...")
            
            url = f"{self.slotslaunch_base_url}/games"
            
            # CORRECT headers format - ALWAYS use spikeup.com as Origin
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': self.default_domain,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Initial request to get meta info
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
                    self.log_debug("No games found from API, using fallback")
                    return self.get_fallback_games(count)
                
                # Fetch from multiple random pages to get variety
                all_games = []
                pages_to_fetch = min(3, last_page)  # Fetch from up to 3 random pages
                
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
                        
                        # Validate and add games
                        for game in page_games:
                            validated_game = self.validate_game_data(game)
                            if validated_game and not any(g['slug'] == validated_game['slug'] for g in all_games):
                                all_games.append(validated_game)
                                self.log_debug(f"Added game: {validated_game['title']}")
                                
                                if len(all_games) >= count:
                                    break
                    
                    if len(all_games) >= count:
                        break
                
                # Randomly select final games
                if len(all_games) > count:
                    all_games = random.sample(all_games, count)
                
                self.log_debug(f"Successfully processed {len(all_games)} valid games")
                return all_games if all_games else self.get_fallback_games(count)
                
            else:
                self.log_debug(f"API Error {response.status_code}: {response.text[:200]}")
                return self.get_fallback_games(count)
                
        except Exception as e:
            self.log_debug(f"Exception fetching games: {e}")
            traceback.print_exc()
            return self.get_fallback_games(count)
    
    def fetch_additional_games(self, count=10, existing_games=None):
        """Fetch additional games avoiding duplicates"""
        self.log_debug(f"Fetching {count} additional games...")
        
        existing_slugs = set()
        if existing_games:
            for game in existing_games:
                if game.get('slug'):
                    existing_slugs.add(game['slug'])
        
        # Fetch more games than needed
        additional_games = self.fetch_slotslaunch_games(count * 3)
        
        # Filter out duplicates
        unique_games = []
        for game in additional_games:
            if game.get('slug') not in existing_slugs:
                unique_games.append(game)
                existing_slugs.add(game['slug'])
                
                if len(unique_games) >= count:
                    break
        
        # Fill with fallback if needed
        if len(unique_games) < count:
            self.log_debug(f"Only found {len(unique_games)} unique games, adding fallback...")
            fallback_games = self.get_fallback_games(count * 2)
            
            for game in fallback_games:
                if game.get('slug') not in existing_slugs:
                    unique_games.append(game)
                    existing_slugs.add(game['slug'])
                    
                    if len(unique_games) >= count:
                        break
        
        self.log_debug(f"Returning {len(unique_games)} additional games")
        return unique_games[:count]
    
    def generate_fallback_image_url(self, game_title):
        """Generate a themed fallback image URL based on game title"""
        title_lower = game_title.lower()
        
        if any(word in title_lower for word in ['gold', 'treasure', 'pharaoh', 'egypt']):
            return "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=400&h=267&fit=crop"
        elif any(word in title_lower for word in ['diamond', 'crystal', 'gem']):
            return "https://images.unsplash.com/photo-1556745757-8d76bdb6984b?w=400&h=267&fit=crop"
        elif any(word in title_lower for word in ['vegas', 'casino', 'neon']):
            return "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=400&h=267&fit=crop"
        elif any(word in title_lower for word in ['dragon', 'fire', 'magic']):
            return "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=267&fit=crop"
        else:
            return "https://images.unsplash.com/photo-1551434678-e076c223a692?w=400&h=267&fit=crop"
    
    def test_slotslaunch_api(self, domain_name="spikeup.com"):
        """Test SlotsLaunch API connection"""
        self.log_debug("Testing SlotsLaunch API connection...")
        
        url = f"{self.slotslaunch_base_url}/games"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Origin': self.default_domain
        }
        
        params = {
            'token': self.slotslaunch_token,
            'page': 1,
            'per_page': 5,
            'published': 1
        }
        
        try:
            self.respect_rate_limit()
            response = requests.get(url, params=params, headers=headers, timeout=10)
            self.log_debug(f"Test API Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                games = data.get('data', [])
                meta = data.get('meta', {})
                
                self.log_debug(f"✅ API Test Success! Found {len(games)} games")
                self.log_debug(f"Total games available: {meta.get('total', 0)}")
                return True
            else:
                self.log_debug(f"❌ API Test Failed: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.log_debug(f"❌ API Test Exception: {e}")
            return False
    
    def get_fallback_games(self, count=10):
        """Enhanced fallback games with better data structure"""
        self.log_debug(f"Using {count} fallback games...")
        
        fallback_games = [
            {
                "title": "Golden Pharaoh's Fortune",
                "url": "/games/golden-pharaoh",
                "cta_text": "Play Now",
                "image": "images/games/golden-pharaoh.jpg",
                "slug": "golden-pharaoh",
                "game_id": "golden-pharaoh",
                "provider": "Featured"
            },
            {
                "title": "Diamond Destiny",
                "url": "/games/diamond-destiny",
                "cta_text": "Play Now",
                "image": "images/games/diamond-destiny.jpg",
                "slug": "diamond-destiny",
                "game_id": "diamond-destiny",
                "provider": "Featured"
            },
            {
                "title": "Vegas Lightning",
                "url": "/games/vegas-lightning",
                "cta_text": "Play Now",
                "image": "images/games/vegas-lightning.jpg",
                "slug": "vegas-lightning",
                "game_id": "vegas-lightning",
                "provider": "Featured"
            },
            {
                "title": "Dragon's Fire",
                "url": "/games/dragons-fire",
                "cta_text": "Play Now",
                "image": "images/games/dragons-fire.jpg",
                "slug": "dragons-fire",
                "game_id": "dragons-fire",
                "provider": "Featured"
            },
            {
                "title": "Ocean Treasures",
                "url": "/games/ocean-treasures",
                "cta_text": "Play Now",
                "image": "images/games/ocean-treasures.jpg",
                "slug": "ocean-treasures",
                "game_id": "ocean-treasures",
                "provider": "Featured"
            },
            {
                "title": "Wild West Gold Rush",
                "url": "/games/wild-west-gold",
                "cta_text": "Play Now",
                "image": "images/games/wild-west-gold.jpg",
                "slug": "wild-west-gold",
                "game_id": "wild-west-gold",
                "provider": "Featured"
            },
            {
                "title": "Space Adventure",
                "url": "/games/space-adventure",
                "cta_text": "Play Now",
                "image": "images/games/space-adventure.jpg",
                "slug": "space-adventure",
                "game_id": "space-adventure",
                "provider": "Featured"
            },
            {
                "title": "Mystical Forest",
                "url": "/games/mystical-forest",
                "cta_text": "Play Now",
                "image": "images/games/mystical-forest.jpg",
                "slug": "mystical-forest",
                "game_id": "mystical-forest",
                "provider": "Featured"
            },
            {
                "title": "Crystal Palace",
                "url": "/games/crystal-palace",
                "cta_text": "Play Now",
                "image": "images/games/crystal-palace.jpg",
                "slug": "crystal-palace",
                "game_id": "crystal-palace",
                "provider": "Featured"
            },
            {
                "title": "Pirate's Treasure",
                "url": "/games/pirates-treasure",
                "cta_text": "Play Now",
                "image": "images/games/pirates-treasure.jpg",
                "slug": "pirates-treasure",
                "game_id": "pirates-treasure",
                "provider": "Featured"
            },
            {
                "title": "Aztec Gold",
                "url": "/games/aztec-gold",
                "cta_text": "Play Now",
                "image": "images/games/aztec-gold.jpg",
                "slug": "aztec-gold",
                "game_id": "aztec-gold",
                "provider": "Featured"
            },
            {
                "title": "Lucky Leprechaun",
                "url": "/games/lucky-leprechaun",
                "cta_text": "Play Now",
                "image": "images/games/lucky-leprechaun.jpg",
                "slug": "lucky-leprechaun",
                "game_id": "lucky-leprechaun",
                "provider": "Featured"
            }
        ]
        
        # Download fallback images if needed
        for game in fallback_games[:count]:
            if game['image'].startswith('images/'):
                image_filename = game['image'].split('/')[-1]
                image_path = self.images_dir / image_filename
                if not image_path.exists():
                    fallback_url = self.generate_fallback_image_url(game['title'])
                    downloaded_path = self.download_image(fallback_url, image_filename)
                    if downloaded_path:
                        game['image'] = downloaded_path
        
        return fallback_games[:count]
    
    def clean_json_response(self, content):
        """Clean and extract JSON from API response"""
        if not content:
            return None
            
        # Remove any markdown code blocks
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*$', '', content)
        
        # Find JSON content between { } or [ ]
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
    
    def select_theme_font(self, chosen_theme):
        """Select appropriate font based on theme"""
        theme_name = chosen_theme.get('name', '').lower()
        theme_desc = chosen_theme.get('description', '').lower()
        
        if any(word in theme_name + theme_desc for word in ['egypt', 'pharaoh', 'pyramid', 'ancient']):
            return 'Cinzel'
        elif any(word in theme_name + theme_desc for word in ['vegas', 'neon', 'electric', 'bright']):
            return 'Oswald'
        elif any(word in theme_name + theme_desc for word in ['luxury', 'elegant', 'sophisticated', 'premium']):
            return 'Playfair Display'
        elif any(word in theme_name + theme_desc for word in ['west', 'saloon', 'cowboy', 'frontier']):
            return 'Rye'
        elif any(word in theme_name + theme_desc for word in ['mystical', 'magic', 'dragon', 'fantasy']):
            return 'Cormorant Garamond'
        else:
            return 'Inter'
    
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
            self.log_debug(f"Raw color response: {repr(content[:100])}...")
            
            colors = self.clean_json_response(content)
            if colors and isinstance(colors, dict) and 'primary_color' in colors:
                # Ensure all required colors exist
                required_keys = ['primary_color', 'secondary_color', 'accent_color', 'background_start', 'background_end']
                if all(key in colors for key in required_keys):
                    # Fill missing colors
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
        """Get cohesive colors based on the specific theme"""
        theme_name = chosen_theme['name'].lower()
        theme_desc = chosen_theme['description'].lower()
        
        if any(word in theme_name + theme_desc for word in ['egypt', 'pharaoh', 'pyramid', 'ancient']):
            return {
                "primary_color": "#D4A574",
                "secondary_color": "#8B4513",
                "accent_color": "#FFD700",
                "background_start": "#1A1A2E",
                "background_end": "#16213E",
                "primary_hover": "#C19A68",
                "secondary_hover": "#7A3F12",
                "sidebar_start": "#1A1A2E",
                "sidebar_end": "#16213E",
                "footer_bg": "#16213E"
            }
        elif any(word in theme_name + theme_desc for word in ['vegas', 'neon', 'electric', 'bright']):
            return {
                "primary_color": "#00D4FF",
                "secondary_color": "#8A2BE2",
                "accent_color": "#FF1493",
                "background_start": "#0A0A1A",
                "background_end": "#1A0A2E",
                "primary_hover": "#00B8E6",
                "secondary_hover": "#7B27CC",
                "sidebar_start": "#0A0A1A",
                "sidebar_end": "#1A0A2E",
                "footer_bg": "#1A0A2E"
            }
        else:
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
        
        # Fetch real games from SlotsLaunch API
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
            self.log_debug(f"Raw content response: {repr(content[:100])}...")
            
            data = self.clean_json_response(content)
            if data and isinstance(data, dict) and 'sections' in data:
                # Add real games to sections
                data['sections'][0]['items'] = featured_games
                data['sections'][1]['items'] = new_games
                
                self.log_debug(f"Content generated successfully with games")
                return data
            else:
                self.log_debug("Invalid content response, using fallback")
                raise ValueError("Invalid response format")
            
        except Exception as e:
            self.log_debug(f"Error generating content: {e}")
            # Fallback content with real games
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
    
    def generate_hero_image(self, chosen_theme, site_name):
        """Generate hero background image using DALL-E"""
        prompt = f"""Create a stunning social casino hero background image for "{site_name}".
        
        Theme: {chosen_theme['name']} - {chosen_theme['description']}
        
        Create a casino/gaming themed image with:
        - Slot machine elements and casino atmosphere
        - Rich, vibrant colors matching the theme
        - Luxurious and exciting gaming environment
        - NO text, logos, or readable words
        - Landscape orientation perfect for web hero section"""
        
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",
                quality="standard",
                n=1
            )
            
            # Download and save image
            image_url = response.data[0].url
            filename = f"hero-{site_name.lower().replace(' ', '-')}.jpg"
            filepath = self.output_dir / filename
            
            self.log_debug(f"Downloading hero image...")
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            
            self.log_debug(f"Hero image saved: {filename}")
            return filename
            
        except Exception as e:
            self.log_debug(f"Error generating hero image: {e}")
            return "hero-bg.jpg"
    
    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB values"""
        try:
            hex_color = hex_color.lstrip('#')
            return ', '.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))
        except:
            return "255, 255, 255"
    
    def build_website_data(self, site_name, domain_name, chosen_theme, colors, content, hero_image):
        """Build complete website data structure"""
        selected_font = self.select_theme_font(chosen_theme)
        
        website_data = {
            'site_name': site_name,
            'site_tagline': content['tagline'],
            'primary_font': selected_font,
            
            'colors': {
                'primary': colors['primary_color'],
                'secondary': colors['secondary_color'],
                'accent': colors['accent_color'],
                'background_start': colors.get('background_start', '#0a0a0a'),
                'background_end': colors.get('background_end', '#16213e'),
                'primary_hover': colors.get('primary_hover', colors['primary_color']),
                'secondary_hover': colors.get('secondary_hover', colors['secondary_color']),
                'sidebar_start': colors.get('sidebar_start', '#1e1e2e'),
                'sidebar_end': colors.get('sidebar_end', '#2a2a4a'),
                'footer_bg': colors.get('footer_bg', '#1e293b'),
                'about_bg_start': f"rgba({self.hex_to_rgb(colors['primary_color'])}, 0.05)",
                'about_bg_end': f"rgba({self.hex_to_rgb(colors['accent_color'])}, 0.05)"
            },
            
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
            },
            
            'footer': {
                'disclaimer': {
                    'title': 'Disclaimer',
                    'text': content['disclaimer']
                },
                'copyright_year': datetime.now().year,
                'domain_name': domain_name,
                'additional_text': ''
            }
        }
        
        self.log_debug(f"Website data built with {len(content['sections'])} sections")
        return website_data
    
    def build_games_page_data(self, site_name, domain_name, colors, all_games, content):
        """Build games page data structure with enhanced debugging"""
        selected_font = self.select_theme_font({'name': '', 'description': ''})
        
        games_data = {
            'site_name': site_name,
            'primary_font': selected_font,
            
            'colors': {
                'primary': colors['primary_color'],
                'secondary': colors['secondary_color'],
                'accent': colors['accent_color'],
                'background_start': colors.get('background_start', '#0a0a0a'),
                'background_end': colors.get('background_end', '#16213e'),
                'primary_hover': colors.get('primary_hover', colors['primary_color']),
                'secondary_hover': colors.get('secondary_hover', colors['secondary_color']),
                'sidebar_start': colors.get('sidebar_start', '#1e1e2e'),
                'sidebar_end': colors.get('sidebar_end', '#2a2a4a'),
                'footer_bg': colors.get('footer_bg', '#1e293b'),
            },
            
            'all_games': all_games,
            'total_games': len(all_games),
            
            'footer': {
                'disclaimer': {
                    'title': 'Disclaimer',
                    'text': content['disclaimer']
                },
                'copyright_year': datetime.now().year,
                'domain_name': domain_name,
                'additional_text': ''
            }
        }
        
        self.log_debug(f"Games page data built with {len(all_games)} games")
        
        # Debug: Log sample games
        for i, game in enumerate(all_games[:3]):
            self.log_debug(f"Game {i+1}: {game['title']} - {game['url']} - {game['image']}")
        
        return games_data
    
    def render_website(self, website_data, template_path):
        """Render the final HTML using Jinja2 template with enhanced debugging"""
        try:
            self.log_debug(f"Rendering template: {template_path}")
            
            # Read template file
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Create Jinja2 template
            template = Template(template_content)
            
            # Debug template data
            if 'content_sections' in website_data:
                self.log_debug(f"Rendering homepage with {len(website_data['content_sections'])} sections")
                for i, section in enumerate(website_data['content_sections']):
                    games_count = len(section.get('items', []))
                    self.log_debug(f"Section {i}: {games_count} games")
            elif 'all_games' in website_data:
                self.log_debug(f"Rendering games page with {len(website_data['all_games'])} games")
            
            # Render HTML
            html_output = template.render(**website_data)
            
            # Determine output filename
            if 'content_sections' in website_data:
                output_filename = f"{website_data['site_name'].lower().replace(' ', '-')}-website.html"
            else:
                output_filename = f"{website_data['site_name'].lower().replace(' ', '-')}-games.html"
            
            output_path = self.output_dir / output_filename
            
            # Save rendered HTML
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_output)
            
            self.log_debug(f"Template rendered successfully: {output_path}")
            return output_path
            
        except FileNotFoundError:
            self.log_debug(f"Template file not found: {template_path}")
            return None
        except Exception as e:
            self.log_debug(f"Error rendering website: {e}")
            traceback.print_exc()
            return None
    
    def generate_complete_website(self, domain_name):
        """Complete workflow to generate website and games page"""
        print(f"🚀 Starting website generation for: {domain_name}")
        print("=" * 50)
        
        # Step 0: Test API connection
        print(f"🧪 Testing SlotsLaunch API connection...")
        api_test_result = self.test_slotslaunch_api()
        if api_test_result:
            print("✅ SlotsLaunch API connection successful!")
        else:
            print("⚠️ SlotsLaunch API connection failed, will use fallback games")
        
        # Step 1: Extract site name
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
        
        # Step 3: Generate color palette
        print(f"🎨 Generating color palette...")
        colors = self.generate_color_palette(chosen_theme)
        print(f"✅ Colors generated: {colors['primary_color']}, {colors['secondary_color']}, {colors['accent_color']}")
        
        # Step 4: Generate content (includes fetching real games)
        print(f"✍️  Generating website content...")
        content = self.generate_content(site_name, chosen_theme, domain_name)
        print(f"✅ Content generated: {content['hero_title']}")
        
        # Step 5: Generate hero image
        print(f"🖼️  Generating hero image...")
        hero_image = self.generate_hero_image(chosen_theme, site_name)
        
        # Step 6: Build complete homepage data structure
        print(f"🏗️  Building homepage data...")
        website_data = self.build_website_data(site_name, domain_name, chosen_theme, colors, content, hero_image)
        
        # Step 7: Render homepage
        print(f"🎯 Rendering homepage...")
        template_path = "homepage_template.html"
        homepage_path = self.render_website(website_data, template_path)
        
        # Step 8: Fetch additional games for games page
        print(f"🎮 Fetching additional games for games page...")
        homepage_games = content['sections'][0]['items'] + content['sections'][1]['items']
        additional_games = self.fetch_additional_games(10, homepage_games)
        all_games = homepage_games + additional_games
        
        print(f"📊 Games Summary:")
        print(f"   Homepage games: {len(homepage_games)}")
        print(f"   Additional games: {len(additional_games)}")
        print(f"   Total games: {len(all_games)}")
        
        # Step 9: Build games page data structure
        print(f"🏗️  Building games page data...")
        games_data = self.build_games_page_data(site_name, domain_name, colors, all_games, content)
        
        # Step 10: Render games page
        print(f"🎯 Rendering games page...")
        games_template_path = "games_template.html"
        games_path = self.render_website(games_data, games_template_path)
        
        if homepage_path and games_path:
            print("\n" + "=" * 50)
            print("🎉 Website Generated Successfully!")
            print("=" * 50)
            print(f"📁 Homepage file: {homepage_path}")
            print(f"📁 Games page file: {games_path}")
            print(f"📂 Images saved to: {self.images_dir}")
            print(f"🎨 Primary color: {colors['primary_color']}")
            print(f"🎭 Theme: {chosen_theme['name']}")
            print(f"🏠 Hero title: {content['hero_title']}")
            print(f"🖼️  Hero image: {hero_image}")
            print(f"🎮 Total games: {len(all_games)} (Homepage: {len(homepage_games)}, Additional: {len(additional_games)})")
            print("=" * 50)
            return homepage_path, games_path
        else:
            print("❌ Failed to generate website")
            return None, None


def main():
    """Main function to run the website generator"""
    print("🌟 Dynamic Casino Website Generator")
    print("=" * 50)
    
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
        generator = DynamicWebsiteGenerator(api_key)
        
        # Generate website
        homepage_path, games_path = generator.generate_complete_website(domain)
        
        if homepage_path and games_path:
            print(f"\n🎯 Next steps:")
            print(f"1. Open {homepage_path} in your browser")
            print(f"2. Open {games_path} in your browser")
            print(f"3. Copy the hero image to the same folder as the HTML files")
            print(f"4. Copy the 'images' folder to the same location as the HTML files")
            print(f"5. Game thumbnails are saved locally in '{generator.images_dir}'")
            print(f"6. All games have local URLs pointing to /games/[slug] pages")
            print(f"7. Customize further if needed")
            print("\n✨ Happy website building!")
        
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