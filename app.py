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
        print(f"🔧 Initialized with SlotsLaunch API token: {self.slotslaunch_token[:10]}...")
        print(f"📍 Using whitelisted domain: {self.default_domain}")
        print(f"📁 Images will be saved to: {self.images_dir}")
    
    def download_image(self, image_url, filename):
        """Download image from URL and save locally"""
        try:
            # Create full path
            filepath = self.images_dir / filename
            
            # Skip if already exists
            if filepath.exists():
                print(f"✅ Image already exists: {filename}")
                return f"images/games/{filename}"
            
            print(f"📥 Downloading: {filename}")
            response = requests.get(image_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Save image
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Saved: {filename}")
            return f"images/games/{filename}"
            
        except Exception as e:
            print(f"❌ Failed to download {filename}: {e}")
            return None
    
    def sanitize_filename(self, name):
        """Sanitize filename for safe file system usage"""
        # Remove special characters and replace spaces
        safe_name = re.sub(r'[^a-zA-Z0-9\-_]', '-', name.lower())
        # Remove multiple dashes
        safe_name = re.sub(r'-+', '-', safe_name)
        # Remove leading/trailing dashes
        safe_name = safe_name.strip('-')
        return safe_name
    
    def respect_rate_limit(self):
        """Implement rate limiting for SlotsLaunch API (0.5-2 requests per second)"""
        # Conservative rate limiting: 1 request per 2 seconds (0.5 r/s)
        min_interval = 2.0  
        time_since_last = time.time() - self.last_api_call
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            print(f"⏱️  Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        
        self.last_api_call = time.time()
        
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
        
        # Clean up common issues
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"📝 Raw content: {repr(content[:200])}...")
            return None
    
    def select_theme_font(self, chosen_theme):
        """Select appropriate font based on theme"""
        theme_name = chosen_theme['name'].lower()
        theme_desc = chosen_theme['description'].lower()
        
        # Egyptian/Ancient themes
        if any(word in theme_name + theme_desc for word in ['egypt', 'pharaoh', 'pyramid', 'ancient', 'temple', 'hieroglyph']):
            return 'Cinzel'
        
        # Vegas/Neon themes  
        elif any(word in theme_name + theme_desc for word in ['vegas', 'neon', 'electric', 'bright', 'casino']):
            return 'Oswald'
            
        # Luxury/Elegant themes
        elif any(word in theme_name + theme_desc for word in ['luxury', 'elegant', 'sophisticated', 'premium', 'diamond', 'crystal']):
            return 'Playfair Display'
            
        # Wild West themes
        elif any(word in theme_name + theme_desc for word in ['west', 'saloon', 'cowboy', 'frontier', 'rustic']):
            return 'Rye'
            
        # Mystical/Fantasy themes
        elif any(word in theme_name + theme_desc for word in ['mystical', 'magic', 'dragon', 'fantasy', 'enchanted']):
            return 'Cormorant Garamond'
            
        # Default modern font
        else:
            return 'Inter'
    
    def fetch_slotslaunch_games(self, count=10, domain_name="spikeup.com"):
        """Fetch games from SlotsLaunch API using CORRECT format that complies with their requirements"""
        try:
            print(f"🎰 Fetching {count} games from SlotsLaunch API...")
            print(f"📍 Using authorized Origin: {self.default_domain} (always spikeup.com)")
            
            url = f"{self.slotslaunch_base_url}/games"
            
            # CORRECT headers format - ALWAYS use spikeup.com as Origin (whitelisted domain)
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': self.default_domain  # ALWAYS spikeup.com - the whitelisted domain
            }
            
            # Token goes in URL parameters (CORRECT format)
            initial_params = {
                'token': self.slotslaunch_token,  # CORRECT: Token as parameter
                'page': 1,
                'per_page': 20,  # Small request to get meta info
                'published': 1,  # Integer 1 (not boolean)
                'order': 'asc',
                'order_by': 'name'
            }
            
            print("📡 Making initial API request to get total pages...")
            self.respect_rate_limit()  # Rate limiting compliance
            response = requests.get(url, params=initial_params, headers=headers, timeout=10)
            
            print(f"📊 API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                meta = data.get('meta', {})
                last_page = meta.get('last_page', 1)
                total_games = meta.get('total', 0)
                
                print(f"📈 API Meta: {total_games} total games across {last_page} pages")
                
                if last_page == 0 or total_games == 0:
                    print("⚠️ No games found from API, using fallback")
                    return self.get_fallback_games(count)
                
                # Get a random page within valid range
                random_page = random.randint(1, min(last_page, 100))  # Cap at 100 for performance
                
                final_params = {
                    'token': self.slotslaunch_token,
                    'page': random_page,
                    'per_page': count * 2,  # Fetch more than needed
                    'published': 1,
                    'order': 'random'  # Get random games
                }
                
                print(f"🎲 Fetching random page {random_page} of {last_page}...")
                self.respect_rate_limit()  # Rate limiting compliance
                response = requests.get(url, params=final_params, headers=headers, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                games = data.get('data', [])
                
                if not games:
                    print(f"⚠️ No games found on page {random_page}, using fallback")
                    return self.get_fallback_games(count)
                
                print(f"✅ API Response: Found {len(games)} games on page {random_page}")
                
                # Filter and convert games to required format
                valid_games = []
                for game in games:
                    if game.get('name') and game.get('slug'):
                        # Generate local filename for image
                        image_filename = f"{self.sanitize_filename(game['slug'])}.jpg"
                        
                        # Try to download image
                        local_image_path = None
                        if game.get('thumb'):
                            local_image_path = self.download_image(game['thumb'], image_filename)
                        
                        # If download failed, use fallback
                        if not local_image_path:
                            local_image_path = self.generate_fallback_image_url(game['name'])
                        
                        # Create game object with local game page URLs
                        game_obj = {
                            'title': game['name'],
                            'url': f"/games/{game['slug']}",  # Local game page URL
                            'cta_text': 'Play Now',
                            'image': local_image_path,  # Local image path
                            'slug': game['slug'],
                            'game_id': game.get('id', game['slug'])  # Keep ID for reference
                        }
                        valid_games.append(game_obj)
                
                # Randomly select the requested count
                if len(valid_games) >= count:
                    selected_games = random.sample(valid_games, count)
                else:
                    selected_games = valid_games
                
                print(f"🎮 Successfully processed {len(selected_games)} valid games:")
                for game in selected_games[:3]:  # Show first 3 as preview
                    print(f"   🎰 {game['title']} - {game['url']}")
                
                return selected_games
                
            elif response.status_code == 401:
                print("❌ 401 Unauthorized - API token issue")
                print("💡 Check if your API token is correct")
                return self.get_fallback_games(count)
            elif response.status_code == 403:
                print("❌ 403 Forbidden - Domain or IP not authorized")
                print(f"💡 Check if domain '{domain_name}' and your IP are whitelisted")
                return self.get_fallback_games(count)
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error text: {response.text}")
                return self.get_fallback_games(count)
                
        except requests.RequestException as e:
            print(f"❌ Network error fetching games from SlotsLaunch API: {e}")
            print("🔄 Using fallback games instead...")
            return self.get_fallback_games(count)
        except Exception as e:
            print(f"❌ Unexpected error fetching games: {e}")
            print("🔄 Using fallback games instead...")
            return self.get_fallback_games(count)
    
    def generate_fallback_image_url(self, game_title):
        """Generate a themed fallback image URL based on game title"""
        # Use Unsplash with themed searches based on game title
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
            # Default slot machine themed image
            return "https://images.unsplash.com/photo-1551434678-e076c223a692?w=400&h=267&fit=crop"
    
    def test_slotslaunch_api(self, domain_name="spikeup.com"):
        """Test SlotsLaunch API with correct format - always use spikeup.com as Origin"""
        print(f"🧪 Testing SlotsLaunch API...")
        print(f"📍 Using whitelisted Origin: {self.default_domain} (always spikeup.com)")
        
        url = f"{self.slotslaunch_base_url}/games"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Origin': self.default_domain  # ALWAYS spikeup.com - the whitelisted domain
        }
        
        params = {
            'token': self.slotslaunch_token,
            'page': 1,
            'per_page': 5,
            'published': 1
        }
        
        try:
            self.respect_rate_limit()  # Rate limiting compliance
            response = requests.get(url, params=params, headers=headers, timeout=10)
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                games = data.get('data', [])
                meta = data.get('meta', {})
                
                print(f"✅ Success! Found {len(games)} games")
                print(f"📈 Total games available: {meta.get('total', 0)}")
                
                if games:
                    print("🎰 Sample games:")
                    for game in games[:3]:
                        print(f"   - {game.get('name', 'N/A')} ({game.get('provider', 'Unknown')})")
                
                return True
            else:
                print(f"❌ Error: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
    
    def get_fallback_games(self, count=10):
        """Fallback games if API fails - using local game page URLs"""
        print("🔄 Using fallback games with local URLs...")
        
        fallback_games = [
            {
                "title": "Golden Pharaoh's Fortune",
                "url": "/games/golden-pharaoh",  # Local game page URL
                "cta_text": "Play Now",
                "image": "images/games/golden-pharaoh.jpg",  # Local image
                "slug": "golden-pharaoh",
                "game_id": "golden-pharaoh"
            },
            {
                "title": "Diamond Destiny",
                "url": "/games/diamond-destiny",  # Local game page URL
                "cta_text": "Play Now",
                "image": "images/games/diamond-destiny.jpg",  # Local image
                "slug": "diamond-destiny",
                "game_id": "diamond-destiny"
            },
            {
                "title": "Vegas Lightning",
                "url": "/games/vegas-lightning",  # Local game page URL
                "cta_text": "Play Now",
                "image": "images/games/vegas-lightning.jpg",  # Local image
                "slug": "vegas-lightning",
                "game_id": "vegas-lightning"
            },
            {
                "title": "Dragon's Fire",
                "url": "/games/dragons-fire",  # Local game page URL
                "cta_text": "Play Now",
                "image": "images/games/dragons-fire.jpg",  # Local image
                "slug": "dragons-fire",
                "game_id": "dragons-fire"
            },
            {
                "title": "Ocean Treasures",
                "url": "/games/ocean-treasures",  # Local game page URL
                "cta_text": "Play Now",
                "image": "images/games/ocean-treasures.jpg",  # Local image
                "slug": "ocean-treasures",
                "game_id": "ocean-treasures"
            },
            {
                "title": "Wild West Gold Rush",
                "url": "/games/wild-west-gold",  # Local game page URL
                "cta_text": "Play Now",
                "image": "images/games/wild-west-gold.jpg",  # Local image
                "slug": "wild-west-gold",
                "game_id": "wild-west-gold"
            },
            {
                "title": "Space Adventure",
                "url": "/games/space-adventure",  # Local game page URL
                "cta_text": "Play Now",
                "image": "images/games/space-adventure.jpg",  # Local image
                "slug": "space-adventure",
                "game_id": "space-adventure"
            },
            {
                "title": "Mystical Forest",
                "url": "/games/mystical-forest",  # Local game page URL
                "cta_text": "Play Now",
                "image": "images/games/mystical-forest.jpg",  # Local image
                "slug": "mystical-forest",
                "game_id": "mystical-forest"
            }
        ]
        
        # Download fallback images if needed
        for game in fallback_games[:count]:
            if game['image'].startswith('images/'):
                # Check if local image exists, if not, download a fallback
                image_path = self.images_dir / game['image'].split('/')[-1]
                if not image_path.exists():
                    fallback_url = self.generate_fallback_image_url(game['title'])
                    downloaded_path = self.download_image(fallback_url, game['image'].split('/')[-1])
                    if downloaded_path:
                        game['image'] = downloaded_path
        
        return fallback_games[:count]
    
    def generate_theme_ideas(self, domain_name):
        """Generate 3 theme ideas for the social casino website"""
        site_name = domain_name.replace('.com', '').replace('.', ' ').title()
        
        prompt = f"""You must respond with ONLY valid JSON. No explanations, no markdown, just JSON.

Generate 3 unique SOCIAL CASINO themed website ideas for {domain_name}. 
Analyze the domain name "{site_name}" and create casino/slots themes based on its meaning.

For example, if domain was "anubisslots.com":
- Egyptian themed casino with pharaohs, pyramids, golden slots
- Desert oasis casino with palm trees and luxury
- Ancient temple slots with mystical elements

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
            print(f"🔍 Raw API response: {repr(content[:100])}...")
            
            themes = self.clean_json_response(content)
            if themes and isinstance(themes, list) and len(themes) >= 3:
                return themes[:3]
            else:
                print("❌ Invalid theme response, using fallback")
                raise ValueError("Invalid response format")
            
        except Exception as e:
            print(f"❌ Error generating themes: {e}")
            # Fallback casino themes
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
        """Generate color palette based on chosen theme with better cohesion"""
        prompt = f"""You must respond with ONLY valid JSON. No explanations, no markdown, just JSON.

Generate a cohesive and harmonious color palette for this casino website theme:
Name: {chosen_theme['name']}
Description: {chosen_theme['description']}
Mood: {', '.join(chosen_theme['mood'])}
Target Feel: {chosen_theme['target_feel']}

IMPORTANT COLOR RULES:
- Use a limited palette with good contrast
- Colors must work well together (no clashing)
- Primary and secondary should be complementary or analogous
- Background colors should be dark for casino atmosphere
- Accent color should pop but not clash
- All colors should feel cohesive and professional

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
                    {"role": "system", "content": "You are a professional color palette generator. Create cohesive, harmonious color schemes that work well together. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent results
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            print(f"🎨 Raw color response: {repr(content[:100])}...")
            
            colors = self.clean_json_response(content)
            if colors and isinstance(colors, dict) and 'primary_color' in colors:
                # Validate that we have all required colors
                required_keys = ['primary_color', 'secondary_color', 'accent_color', 'background_start', 'background_end']
                if all(key in colors for key in required_keys):
                    # Ensure hover colors exist
                    if 'primary_hover' not in colors:
                        colors['primary_hover'] = self.darken_color(colors['primary_color'], 0.1)
                    if 'secondary_hover' not in colors:
                        colors['secondary_hover'] = self.darken_color(colors['secondary_color'], 0.1)
                    if 'sidebar_start' not in colors:
                        colors['sidebar_start'] = colors['background_start']
                    if 'sidebar_end' not in colors:
                        colors['sidebar_end'] = colors['background_end']
                    if 'footer_bg' not in colors:
                        colors['footer_bg'] = colors['background_end']
                    
                    return colors
                else:
                    print("❌ Missing required color keys, using theme-based fallback")
                    raise ValueError("Missing required colors")
            else:
                print("❌ Invalid color response, using theme-based fallback")
                raise ValueError("Invalid response format")
            
        except Exception as e:
            print(f"❌ Error generating colors: {e}")
            # Use theme-based fallback colors instead of generic ones
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
            return hex_color  # Return original if darkening fails
    
    def get_theme_based_colors(self, chosen_theme):
        """Get cohesive colors based on the specific theme"""
        theme_name = chosen_theme['name'].lower()
        theme_desc = chosen_theme['description'].lower()
        
        # Egyptian/Ancient themes - Gold, deep blues, warm tones
        if any(word in theme_name + theme_desc for word in ['egypt', 'pharaoh', 'pyramid', 'ancient', 'temple', 'hieroglyph', 'anubis']):
            return {
                "primary_color": "#D4A574",      # Warm gold
                "secondary_color": "#8B4513",    # Saddle brown
                "accent_color": "#FFD700",       # Bright gold
                "background_start": "#1A1A2E",  # Deep purple-blue
                "background_end": "#16213E",     # Dark blue
                "primary_hover": "#C19A68",     # Darker gold
                "secondary_hover": "#7A3F12",   # Darker brown
                "sidebar_start": "#1A1A2E",     # Deep purple-blue
                "sidebar_end": "#16213E",       # Dark blue
                "footer_bg": "#16213E"          # Dark blue
            }
        
        # Vegas/Neon themes - Electric blues, purples, bright colors
        elif any(word in theme_name + theme_desc for word in ['vegas', 'neon', 'electric', 'bright', 'casino']):
            return {
                "primary_color": "#00D4FF",      # Electric blue
                "secondary_color": "#8A2BE2",    # Blue violet
                "accent_color": "#FF1493",       # Deep pink
                "background_start": "#0A0A1A",  # Very dark blue
                "background_end": "#1A0A2E",    # Dark purple
                "primary_hover": "#00B8E6",     # Darker electric blue
                "secondary_hover": "#7B27CC",   # Darker violet
                "sidebar_start": "#0A0A1A",     # Very dark blue
                "sidebar_end": "#1A0A2E",       # Dark purple
                "footer_bg": "#1A0A2E"          # Dark purple
            }
            
        # Luxury/Elegant themes - Deep purples, golds, sophisticated colors
        elif any(word in theme_name + theme_desc for word in ['luxury', 'elegant', 'sophisticated', 'premium', 'diamond', 'crystal']):
            return {
                "primary_color": "#6B46C1",      # Rich purple
                "secondary_color": "#D4A574",    # Elegant gold
                "accent_color": "#E5E7EB",       # Platinum silver
                "background_start": "#111827",  # Rich dark gray
                "background_end": "#1F2937",    # Dark blue-gray
                "primary_hover": "#5B21B6",     # Darker purple
                "secondary_hover": "#C19A68",   # Darker gold
                "sidebar_start": "#111827",     # Rich dark gray
                "sidebar_end": "#1F2937",       # Dark blue-gray
                "footer_bg": "#1F2937"          # Dark blue-gray
            }
            
        # Wild West themes - Warm browns, oranges, rustic colors
        elif any(word in theme_name + theme_desc for word in ['west', 'saloon', 'cowboy', 'frontier', 'rustic']):
            return {
                "primary_color": "#D2691E",      # Chocolate orange
                "secondary_color": "#8B4513",    # Saddle brown
                "accent_color": "#CD853F",       # Peru
                "background_start": "#2D1B0E",  # Dark brown
                "background_end": "#3E2723",    # Darker brown
                "primary_hover": "#C25E1A",     # Darker orange
                "secondary_hover": "#7A3F12",   # Darker brown
                "sidebar_start": "#2D1B0E",     # Dark brown
                "sidebar_end": "#3E2723",       # Darker brown
                "footer_bg": "#3E2723"          # Darker brown
            }
            
        # Mystical/Fantasy themes - Deep purples, blues, magical colors
        elif any(word in theme_name + theme_desc for word in ['mystical', 'magic', 'dragon', 'fantasy', 'enchanted']):
            return {
                "primary_color": "#7C3AED",      # Violet
                "secondary_color": "#059669",    # Emerald green
                "accent_color": "#F59E0B",       # Amber
                "background_start": "#1E1B4B",  # Deep indigo
                "background_end": "#312E81",    # Dark indigo
                "primary_hover": "#6D28D9",     # Darker violet
                "secondary_hover": "#047857",   # Darker emerald
                "sidebar_start": "#1E1B4B",     # Deep indigo
                "sidebar_end": "#312E81",       # Dark indigo
                "footer_bg": "#312E81"          # Dark indigo
            }
            
        # Default modern casino theme - Blues, teals, sophisticated
        else:
            return {
                "primary_color": "#0EA5E9",      # Sky blue
                "secondary_color": "#8B5CF6",    # Violet
                "accent_color": "#10B981",       # Emerald
                "background_start": "#0F172A",  # Dark slate
                "background_end": "#1E293B",    # Slate
                "primary_hover": "#0284C7",     # Darker sky blue
                "secondary_hover": "#7C3AED",   # Darker violet
                "sidebar_start": "#0F172A",     # Dark slate
                "sidebar_end": "#1E293B",       # Slate
                "footer_bg": "#1E293B"          # Slate
            }
    
    def generate_content(self, site_name, chosen_theme, target_domain):
        """Generate all website content based on theme with real games from SlotsLaunch API"""
        
        # Fetch real games from SlotsLaunch API (always using spikeup.com as authorized origin)
        print(f"🎮 Fetching games for website: {target_domain}")
        print(f"📍 API calls using authorized origin: {self.default_domain}")
        featured_games = self.fetch_slotslaunch_games(6)  # Always use default domain for API
        new_games = self.fetch_slotslaunch_games(5)       # Always use default domain for API
        
        prompt = f"""You must respond with ONLY valid JSON. No explanations, no markdown, just JSON.

Generate SOCIAL CASINO website content for "{site_name}" based on this theme:
Name: {chosen_theme['name']}
Description: {chosen_theme['description']}
Mood: {', '.join(chosen_theme['mood'])}
Target Feel: {chosen_theme['target_feel']}

Content should be:
- Casino/slots gaming focused
- Exciting and engaging for players
- Themed around the visual elements described
- Include terms like "slots", "games", "jackpots", "wins", etc.

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
            print(f"✍️  Raw content response: {repr(content[:100])}...")
            
            data = self.clean_json_response(content)
            if data and isinstance(data, dict) and 'sections' in data:
                # Add real games to sections
                data['sections'][0]['items'] = featured_games
                data['sections'][1]['items'] = new_games
                
                print(f"✅ Content generated with {len(featured_games)} featured games and {len(new_games)} new games")
                return data
            else:
                print("❌ Invalid content response, using fallback")
                raise ValueError("Invalid response format")
            
        except Exception as e:
            print(f"❌ Error generating content: {e}")
            # Fallback casino content with real games
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
                    "Welcome to the ultimate social casino experience where excitement meets entertainment. Our themed slot machines offer hours of fun with stunning graphics and immersive gameplay.",
                    "Join millions of players who enjoy our premium collection of slot games, from classic fruit machines to modern video slots with exciting bonus features.",
                    "Start your gaming adventure today and discover why we're the top choice for casino entertainment. Play responsibly and enjoy the thrill!"
                ],
                "disclaimer": "This is a social casino for entertainment purposes only. No real money gambling or prizes involved."
            }
    
    def generate_hero_image(self, chosen_theme, site_name):
        """Generate hero background image using DALL-E"""
        prompt = f"""Create a stunning social casino hero background image for "{site_name}".
        
        Theme: {chosen_theme['name']} - {chosen_theme['description']}
        Mood: {', '.join(chosen_theme['mood'])}
        Target Feel: {chosen_theme['target_feel']}
        
        Create a casino/gaming themed image with:
        - Slot machine elements and casino atmosphere
        - Rich, vibrant colors matching the theme
        - Luxurious and exciting gaming environment
        - Visual elements from the theme description
        - High-energy, premium casino feeling
        - NO text, logos, or readable words
        - Landscape orientation perfect for web hero section
        - Professional quality suitable for a casino website"""
        
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
            
            print(f"🖼️  Downloading hero image...")
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            
            print(f"✅ Hero image saved: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error generating hero image: {e}")
            print("📝 Using fallback hero background")
            return "hero-bg.jpg"  # Fallback to a default image
    
    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB values"""
        try:
            hex_color = hex_color.lstrip('#')
            return ', '.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))
        except:
            return "255, 255, 255"  # Fallback to white
    
    def build_website_data(self, site_name, domain_name, chosen_theme, colors, content, hero_image):
        """Build complete website data structure"""
        selected_font = self.select_theme_font(chosen_theme)
        
        return {
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
    
    def render_website(self, website_data, template_path):
        """Render the final HTML using Jinja2 template"""
        try:
            # Read template file
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Create Jinja2 template
            template = Template(template_content)
            
            # Debug: Print data structure
            print(f"🔍 Rendering with {len(website_data['content_sections'])} sections")
            for i, section in enumerate(website_data['content_sections']):
                section_name = "Featured Games" if i == 0 else "New Arrivals"
                print(f"   Section {i}: {section_name} with {len(section['items'])} items")
                # Show sample games
                for j, game in enumerate(section['items'][:2]):
                    print(f"      Game {j+1}: {game['title']} - {game['url']}")
            
            # Render HTML
            html_output = template.render(**website_data)
            
            # Save to output directory
            output_filename = f"{website_data['site_name'].lower().replace(' ', '-')}-website.html"
            output_path = self.output_dir / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_output)
            
            return output_path
            
        except FileNotFoundError:
            print(f"❌ Template file not found: {template_path}")
            return None
        except Exception as e:
            print(f"❌ Error rendering website: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_complete_website(self, domain_name):
        """Complete workflow to generate website"""
        print(f"🚀 Starting website generation for: {domain_name}")
        print("=" * 50)
        
        # Step 0: Test API connection
        print(f"🧪 Testing SlotsLaunch API connection...")
        print(f"⚠️  IMPORTANT: All API calls use '{self.default_domain}' as Origin (whitelisted domain)")
        print(f"⚠️  Game URLs will point to local pages: /games/[slug]")
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
        
        # Step 6: Build complete data structure
        print(f"🏗️  Building website data...")
        selected_font = self.select_theme_font(chosen_theme)
        print(f"🔤 Selected font: {selected_font}")
        website_data = self.build_website_data(site_name, domain_name, chosen_theme, colors, content, hero_image)
        
        # Step 7: Render website
        print(f"🎯 Rendering website...")
        template_path = "dynamic_template.html"
        output_path = self.render_website(website_data, template_path)
        
        if output_path:
            print("\n" + "=" * 50)
            print("🎉 Website Generated Successfully!")
            print("=" * 50)
            print(f"📁 Output file: {output_path}")
            print(f"📂 Images saved to: {self.images_dir}")
            print(f"🎨 Primary color: {colors['primary_color']}")
            print(f"🎭 Theme: {chosen_theme['name']}")
            print(f"🏠 Hero title: {content['hero_title']}")
            print(f"🖼️  Hero image: {hero_image}")
            print(f"🎮 Games: Downloaded locally from SlotsLaunch API")
            print("=" * 50)
            return output_path
        else:
            print("❌ Failed to generate website")
            return None


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
        output_path = generator.generate_complete_website(domain)
        
        if output_path:
            print(f"\n🎯 Next steps:")
            print(f"1. Open {output_path} in your browser")
            print(f"2. Copy the hero image to the same folder as the HTML file")
            print(f"3. Copy the 'images' folder to the same location as the HTML file")
            print(f"4. Game thumbnails are saved locally in '{generator.images_dir}'")
            print(f"5. Game links point to /games/[slug] pages")
            print(f"6. Customize further if needed")
            print("\n✨ Happy website building!")
        
    except openai.AuthenticationError:
        print("❌ Invalid API key. Please check your OPENAI_API_KEY in .env file")
    except openai.RateLimitError:
        print("❌ API rate limit exceeded. Please try again later")
    except openai.APIError as e:
        print(f"❌ OpenAI API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()