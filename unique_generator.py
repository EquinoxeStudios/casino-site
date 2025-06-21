import random
import hashlib
import string
import json
import re
from datetime import datetime
from pathlib import Path
from app import CompleteWebsiteGenerator

class UniqueWebsiteGenerator(CompleteWebsiteGenerator):
    """
    Enhanced website generator with comprehensive uniqueness features
    """
    def __init__(self, openai_api_key, default_domain="spikeup.com"):
        super().__init__(openai_api_key, default_domain)
        self.uniqueness_seed = hashlib.sha256(default_domain.encode()).hexdigest()[:8]
        self.random_state = random.Random(self.uniqueness_seed)
        self._class_map = {}
        self._id_map = {}
        self._css_var_map = {}
        self._func_name_map = {}
        self._var_name_map = {}

        self.class_pools = {
            "sidebar": ["main-sidebar", "side-nav-menu", "navigation-panel", f"sidebar-{self.uniqueness_seed}", "nav-drawer", "side-panel"],
            "sidebar-header": ["sidebar-header", "nav-header", "panel-header", f"header-{self.uniqueness_seed}", "brand-section"],
            "logo": ["logo", "brand-logo", "site-logo", f"logo-{self.uniqueness_seed}", "brand-mark", "site-brand"],
            "sidebar-nav": ["sidebar-nav", "nav-list", "side-menu", f"nav-{self.uniqueness_seed}", "menu-items"],
            "nav-item": ["nav-item", "menu-link", "side-link", f"item-{self.uniqueness_seed}", "nav-link"],
            "sidebar-toggle": ["sidebar-toggle", "toggle-btn", "side-toggle", f"toggle-{self.uniqueness_seed}", "nav-trigger"],
            "main-wrapper": ["main-wrapper", "content-wrapper", "main-content", f"wrapper-{self.uniqueness_seed}", "page-content"],
            "hero": ["hero", "banner", "showcase", f"hero-{self.uniqueness_seed}", "masthead", "jumbotron"],
            "card": ["card", "game-tile", "content-card", f"card-{self.uniqueness_seed}", "item-box"],
            "btn": ["btn", "button", "action-btn", f"btn-{self.uniqueness_seed}", "cta-button"],
            "footer": ["footer", "site-footer", "page-footer", f"footer-{self.uniqueness_seed}", "bottom-section"],
            "content-section": ["content-section", "content-area", "section-block", f"section-{self.uniqueness_seed}"],
            "btn-primary": ["btn-primary", "primary-action", "main-cta", f"primary-{self.uniqueness_seed}"],
            "btn-secondary": ["btn-secondary", "secondary-action", "alt-cta", f"secondary-{self.uniqueness_seed}"],
            "btn-large": ["btn-large", "large-button", "big-cta", f"large-{self.uniqueness_seed}"],
            "footer-content": ["footer-content", "footer-inner", "bottom-content", f"ft-content-{self.uniqueness_seed}"],
            "footer-links": ["footer-links", "footer-nav", "bottom-links", f"ft-links-{self.uniqueness_seed}"],
            "footer-link": ["footer-link", "footer-nav-item", "bottom-link", f"ft-link-{self.uniqueness_seed}"],
            "footer-bottom": ["footer-bottom", "footer-disclaimer", "bottom-text", f"ft-bottom-{self.uniqueness_seed}"],
        }
        self.class_pools.update({
            "mobile-sidebar-toggle": [
                "mobile-sidebar-toggle", "mobile-toggle", "sidebar-mobile-btn", f"mobile-toggle-{self.uniqueness_seed}"
            ],
            "sidebar-overlay": [
                "sidebar-overlay", "sidebar-dimmer", "nav-overlay", f"overlay-{self.uniqueness_seed}"
            ]
        })
        self.id_pools = {
            "sidebar": ["sidebar", "navSidebar", "sidePanel", f"sb-{self.uniqueness_seed}", "navigationDrawer"],
            "mainWrapper": ["mainWrapper", "contentWrap", "mainWrap", f"mw-{self.uniqueness_seed}", "pageWrapper"],
            "sidebarOverlay": ["sidebarOverlay", "navOverlay", "dimmer", f"overlay-{self.uniqueness_seed}"],
            "mobileSidebarToggle": ["mobileSidebarToggle", "mobileMenu", "navToggle", f"mobile-{self.uniqueness_seed}"],
        }
        self.element_tag_pools = {
            "wrapper": ["div", "section", "article"],
            "sidebar": ["nav", "aside", "div"],
            "main": ["main", "section", "div"],
            "hero": ["section", "div", "header"],
            "card": ["article", "div", "li"],
            "footer": ["footer", "section", "div"],
        }
        self.css_var_bases = {
            "spacing": ["--primary-spacing", "--core-space-unit", "--base-gap", f"--space-{self.uniqueness_seed}"],
            "timing": ["--transition-normal", "--speed-default", "--anim-duration", f"--time-{self.uniqueness_seed}"],
            "shadow": ["--shadow-blur", "--blur-amount", "--shadow-spread", f"--blur-{self.uniqueness_seed}"],
        }
        self.func_name_pools = {
            "toggleSidebar": ["toggleSidebar", "toggleNav", "switchPanel", f"toggle{self.uniqueness_seed}"],
            "toggleMobileSidebar": ["toggleMobileSidebar", "toggleMobileNav", "openMobileMenu", f"mobileToggle{self.uniqueness_seed}"],
            "closeMobileSidebar": ["closeMobileSidebar", "closeMobileNav", "hideMobileMenu", f"mobileClose{self.uniqueness_seed}"],
            "handleImageError": ["handleImageError", "onImageFail", "imageErrorHandler", f"imgErr{self.uniqueness_seed}"],
            "handleImageLoad": ["handleImageLoad", "onImageReady", "imageLoadHandler", f"imgLoad{self.uniqueness_seed}"],
        }
        self.var_schemes = ['camelCase', 'snake_case', 'pascalCase']
        self.selected_var_scheme = self.random_state.choice(self.var_schemes)

    @property
    def unique_classes(self):
        if not self._class_map:
            for key, pool in self.class_pools.items():
                self._class_map[key] = self.random_state.choice(pool)
        return self._class_map

    @property
    def unique_ids(self):
        if not self._id_map:
            for key, pool in self.id_pools.items():
                self._id_map[key] = self.random_state.choice(pool)
        return self._id_map

    @property
    def func_names(self):
        if not self._func_name_map:
            for key, pool in self.func_name_pools.items():
                self._func_name_map[key] = self.random_state.choice(pool)
        return self._func_name_map

    def get_element_tag(self, key):
        pool = self.element_tag_pools.get(key, ["div"])
        return self.random_state.choice(pool)

    def generate_unique_css_value(self, base_value, value_type='spacing'):
        if isinstance(base_value, str):
            match = re.match(r'(\d+(?:\.\d+)?)(.*)', base_value)
            if not match:
                return base_value
            num_value = float(match.group(1))
            unit = match.group(2)
            if value_type == 'spacing':
                variation = self.random_state.uniform(-0.1, 0.1)
            elif value_type == 'timing':
                variation = self.random_state.uniform(-0.05, 0.05)
            else:
                variation = self.random_state.uniform(-0.02, 0.02)
            new_value = num_value * (1 + variation)
            if unit in ['px', 's', 'ms']:
                return f"{new_value:.2f}{unit}"
            else:
                return f"{new_value:.3f}{unit}"
        return base_value

    def random_inline_style(self, element_type, base_styles=None):
        styles = []
        if element_type == 'spacing':
            padding = self.generate_unique_css_value('1rem', 'spacing')
            margin = self.generate_unique_css_value('0.5rem', 'spacing')
            if self.random_state.random() < 0.5:
                styles.append(f"padding: {padding}")
            else:
                styles.append(f"margin: {margin}")
        elif element_type == 'animation':
            delay = self.generate_unique_css_value('0.1s', 'timing')
            duration = self.generate_unique_css_value('0.3s', 'timing')
            styles.append(f"transition-delay: {delay}")
            if self.random_state.random() < 0.3:
                styles.append(f"transition-duration: {duration}")
        elif element_type == 'opacity':
            opacity = 1.0 - self.random_state.uniform(0.01, 0.05)
            styles.append(f"opacity: {opacity:.3f}")
        elif element_type == 'color':
            hue_shift = self.random_state.randint(-5, 5)
            styles.append(f"filter: hue-rotate({hue_shift}deg)")
        return "; ".join(styles) if styles else ""

    @property
    def unique_css_vars(self):
        if not self._css_var_map:
            for key, bases in self.css_var_bases.items():
                var_name = self.random_state.choice(bases)
                if key == "spacing":
                    value = self.generate_unique_css_value("1rem", "spacing")
                elif key == "timing":
                    value = self.generate_unique_css_value("0.3s", "timing")
                elif key == "shadow":
                    value = self.generate_unique_css_value("4px", "spacing")
                else:
                    value = self.uniqueness_seed
                self._css_var_map[var_name] = value
        return self._css_var_map

    def inject_random_comments(self, html_content):
        comments = [
            f"<!-- Site ID: {self.uniqueness_seed} -->",
            f"<!-- Generated: {datetime.now().isoformat()} -->",
            f"<!-- Build: {self.random_state.randint(1000, 9999)} -->",
            "<!-- Dynamic content area -->",
            "<!-- Component boundary -->",
            "<!-- Template marker -->",
            f"<!-- Version: {self.random_state.randint(1, 9)}.{self.random_state.randint(0, 99)} -->",
            "<!-- Async loaded -->",
            "<!-- Cache key: {} -->".format(hashlib.md5(str(self.random_state.random()).encode()).hexdigest()[:8]),
        ]
        lines = html_content.split('\n')
        num_comments = self.random_state.randint(3, 7)
        for _ in range(num_comments):
            if len(lines) > 10:
                pos = self.random_state.randint(5, len(lines) - 5)
                comment = self.random_state.choice(comments)
                lines.insert(pos, comment)
        return '\n'.join(lines)

    def add_dom_depth_variation(self, content):
        wrapper_count = self.random_state.randint(0, 2)
        wrappers = []
        for i in range(wrapper_count):
            tag = self.random_state.choice(['div', 'section'])
            class_name = f"wrapper-{self.uniqueness_seed}-{i}"
            data_attr = f'data-level="{i}"'
            wrappers.append(f'<{tag} class="{class_name}" {data_attr}>')
        return wrappers

    def randomize_image_filename(self, original_path, slug):
        hash_part = hashlib.md5(f"{self.uniqueness_seed}{slug}".encode()).hexdigest()[:8]
        timestamp = str(int(self.random_state.random() * 1000000))
        strategies = [
            f"{hash_part}-{slug}.jpg",
            f"{slug}-{hash_part}.webp",
            f"game-{timestamp}.png",
            f"{slug[:10]}-{self.uniqueness_seed}.jpg",
        ]
        return self.random_state.choice(strategies)

    def generate_unique_meta_tags(self):
        meta_tags = []
        generators = ["Custom CMS", "Site Builder", "Web Framework", "Content System"]
        version = f"{self.random_state.randint(1, 9)}.{self.random_state.randint(0, 99)}"
        meta_tags.append(f'<meta name="generator" content="{self.random_state.choice(generators)} v{version}">')
        meta_tags.append(f'<meta name="build-id" content="{self.uniqueness_seed}">')
        viewport_extras = ["", ", viewport-fit=cover", ", user-scalable=no", ", minimum-scale=1"]
        meta_tags.append(f'<meta name="viewport" content="width=device-width, initial-scale=1.0{self.random_state.choice(viewport_extras)}">')
        if self.random_state.random() < 0.5:
            meta_tags.append('<meta http-equiv="X-UA-Compatible" content="IE=edge">')
        if self.random_state.random() < 0.3:
            meta_tags.append('<meta name="format-detection" content="telephone=no">')
        return '\n'.join(meta_tags)

    def generate_base_css(self, colors, primary_font):
        self.log_debug("Generating unique base.css...")
        classes = self.unique_classes
        transition_speed = self.generate_unique_css_value('0.3s', 'timing')
        sidebar_width = self.generate_unique_css_value('280px', 'spacing')
        border_radius = self.generate_unique_css_value('8px', 'spacing')
        css_content = f"""/* Unique Base CSS - Build {self.uniqueness_seed} */
/* Generated on {datetime.now().strftime("%B %d, %Y at %H:%M")} */

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

:root {{
    --primary-color: {colors['primary']};
    --secondary-color: {colors['secondary']};
    --accent-color: {colors['accent']};
    --background-start: {colors.get('background_start', '#0a0a0a')};
    --background-end: {colors.get('background_end', '#16213e')};
    --text-color: {colors.get('text_color', '#fff')};
    {'; '.join([f'{k}: {v}' for k, v in self.unique_css_vars.items()])};
    --primary-font: '{primary_font}', -apple-system, BlinkMacSystemFont, sans-serif;
}}

body {{
    font-family: var(--primary-font);
    line-height: {self.generate_unique_css_value('1.6', 'spacing')};
    color: var(--text-color);
    background: linear-gradient(135deg, var(--background-start) 0%, var(--background-end) 100%);
    min-height: 100vh;
    overflow-x: hidden;
}}

.{classes['sidebar']} {{
    position: fixed;
    left: 0;
    top: 0;
    width: {sidebar_width};
    height: 100vh;
    background: linear-gradient(180deg, {colors.get('sidebar_start', '#1e1e2e')} 0%, {colors.get('sidebar_end', '#2a2a4a')} 100%);
    transition: transform {transition_speed} ease;
    z-index: {self.random_state.randint(1000, 1500)};
}}

.{classes['mobile-sidebar-toggle']} {{
    position: fixed;
    top: 1rem;
    left: 1rem;
    z-index: 1001;
    background: rgba(255,255,255,0.1);
    border: none;
    color: white;
    width: 44px;
    height: 44px;
    border-radius: 8px;
    cursor: pointer;
    backdrop-filter: blur(5px);
    font-size: 1.5rem;
    display: none;
    align-items: center;
    justify-content: center;
}}

.{classes['sidebar-overlay']} {{
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.5);
    z-index: 1500;
    backdrop-filter: blur(2px);
}}
"""
        base_css_path = self.css_dir / "base.css"
        with open(base_css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)
        return base_css_path

    def generate_base_js(self):
        self.log_debug("Generating unique base.js...")
        funcs = self.func_names
        js_content = f"""/* Unique Base JavaScript - Build {self.uniqueness_seed} */
/* Generated on {datetime.now().strftime("%B %d, %Y at %H:%M")} */

function {funcs['toggleSidebar']}() {{
    const sidebar = document.getElementById('{self.unique_ids["sidebar"]}');
    const mainWrapper = document.getElementById('{self.unique_ids["mainWrapper"]}');
    sidebar.classList.toggle('collapsed');
    mainWrapper.classList.toggle('expanded');
    // Removed localStorage usage for compliance
}}

function {funcs['toggleMobileSidebar']}() {{
    const sidebar = document.getElementById('{self.unique_ids["sidebar"]}');
    const overlay = document.getElementById('{self.unique_ids["sidebarOverlay"]}');
    sidebar.classList.toggle('mobile-open');
    overlay.classList.toggle('active');
    document.body.style.overflow = sidebar.classList.contains('mobile-open') ? 'hidden' : '';
}}

function {funcs['closeMobileSidebar']}() {{
    const sidebar = document.getElementById('{self.unique_ids["sidebar"]}');
    const overlay = document.getElementById('{self.unique_ids["sidebarOverlay"]}');
    sidebar.classList.remove('mobile-open');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
}}

function {funcs['handleImageLoad']}(img) {{
    img.classList.remove('loading', 'error');
    img.style.opacity = '0';
    setTimeout(() => {{
        img.style.transition = 'opacity 0.3s ease';
        img.style.opacity = '1';
    }}, 50);
}}

function {funcs['handleImageError']}(img) {{
    img.classList.remove('loading');
    img.classList.add('error');
    console.warn('Image load failed:', img.src);
}}
"""
        # No-op for compatibility with templates
        js_content += "\nfunction trackGameClick() {}\n"
        base_js_path = self.js_dir / "base.js"
        with open(base_js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
        return base_js_path

    def render_template(self, template_filename, data, output_filename):
        self.log_debug(f"Rendering unique template: {template_filename}")
        context = dict(data)
        context.update({
            "unique_classes": self.unique_classes,
            "unique_ids": self.unique_ids,
            "func_names": self.func_names,
            "get_element_tag": self.get_element_tag,
            "random_inline_style": self.random_inline_style,
            "unique_css_vars": self.unique_css_vars,
            "randomize_image_filename": self.randomize_image_filename,
            "uniqueness_seed": self.uniqueness_seed,
            "unique_meta_tags": self.generate_unique_meta_tags(),
        })
        # Add content randomizer and DOM wrapper to context
        context["randomize_content_html"] = self.randomize_content_html
        context["add_dom_depth_variation"] = self.add_dom_depth_variation

        html_output = super().render_template(template_filename, context, output_filename)
        with open(self.output_dir / output_filename, 'r', encoding='utf-8') as f:
            content = f.read()
        content = self.inject_random_comments(content)
        body_attrs = [
            f'data-site="{self.uniqueness_seed}"',
            f'data-build="{self.random_state.randint(1000, 9999)}"',
            f'data-v="{self.random_state.randint(1, 99)}"',
        ]
        content = content.replace('<body>', f'<body {self.random_state.choice(body_attrs)}>')
        with open(self.output_dir / output_filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return self.output_dir / output_filename

    def randomize_content_html(self, text, type_hint="p"):
        """Randomize content HTML for anti-fingerprinting"""
        # Insert invisible Unicode chars
        def insert_invisible(s):
            chars = list(s)
            for i in range(len(chars)):
                if self.random_state.random() < 0.03:
                    chars[i] += "\u200B"  # zero-width space
            return "".join(chars)

        # Randomize paragraph breaks
        if type_hint == "p":
            paras = re.split(r"\n{2,}", text)
            tag = self.random_state.choice(["p", "div", "section"])
            html = "".join(
                f"<{tag}>{insert_invisible(p).replace('\n', '<br>' if self.random_state.random() < 0.5 else '<wbr>')}</{tag}>\n"
                for p in paras if p.strip()
            )
            # Optionally wrap in a semantic element
            if self.random_state.random() < 0.3:
                wrap = self.random_state.choice(["section", "article", "aside"])
                html = f"<{wrap}>{html}</{wrap}>"
            return html

        # Randomize headings
        if type_hint == "h":
            level = self.random_state.choice([1, 2, 3])
            tag = f"h{level}"
            return f"<{tag}>{insert_invisible(text)}</{tag}>"

        # Randomize lists
        if type_hint == "list":
            items = [i.strip() for i in text.split("\n") if i.strip()]
            list_type = self.random_state.choice(["ul", "ol", "dl"])
            if list_type == "dl":
                html = "<dl>\n" + "".join(f"<dt>{insert_invisible(i)}</dt><dd></dd>\n" for i in items) + "</dl>"
            else:
                html = f"<{list_type}>\n" + "".join(f"<li>{insert_invisible(i)}</li>\n" for i in items) + f"</{list_type}>"
            # Optionally wrap in a semantic element
            if self.random_state.random() < 0.2:
                wrap = self.random_state.choice(["nav", "section", "aside"])
                html = f"<{wrap}>{html}</{wrap}>"
            return html

        # Default: just insert invisible chars
        return insert_invisible(text)

    def generate_robots_txt(self):
        crawl_delays = [0.5, 1, 1.5, 2, 2.5]
        robots_content = f"""# Robots.txt - {self.uniqueness_seed}
# Generated: {datetime.now().strftime('%Y-%m-%d')}

User-agent: *
Allow: /
Crawl-delay: {self.random_state.choice(crawl_delays)}

User-agent: AhrefsBot
Disallow: /

Sitemap: https://{self.default_domain}/sitemap.xml

# Build: {self.uniqueness_seed}
"""
        if self.random_state.random() < 0.5:
            robots_content += "\nUser-agent: SemrushBot\nDisallow: /\n"
        robots_path = self.output_dir / "robots.txt"
        with open(robots_path, 'w') as f:
            f.write(robots_content)
        return robots_path

    def generate_htaccess(self):
        cache_times = ['604800', '1209600', '2592000', '2678400']
        htaccess_content = f"""# .htaccess - {self.uniqueness_seed}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/javascript application/json
</IfModule>

# Caching
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType image/jpg "access plus {self.random_state.choice(cache_times)} seconds"
    ExpiresByType image/jpeg "access plus {self.random_state.choice(cache_times)} seconds"
    ExpiresByType image/gif "access plus {self.random_state.choice(cache_times)} seconds"
    ExpiresByType image/png "access plus {self.random_state.choice(cache_times)} seconds"
    ExpiresByType image/webp "access plus {self.random_state.choice(cache_times)} seconds"
    ExpiresByType text/css "access plus {self.random_state.choice(['86400', '172800', '259200'])} seconds"
    ExpiresByType text/javascript "access plus {self.random_state.choice(['86400', '172800'])} seconds"
    ExpiresByType application/javascript "access plus {self.random_state.choice(['86400', '172800'])} seconds"
</IfModule>

# Security headers
<IfModule mod_headers.c>
    Header set X-Content-Type-Options "nosniff"
    Header set X-Frame-Options "{self.random_state.choice(['SAMEORIGIN', 'DENY'])}"
    Header set X-XSS-Protection "1; mode=block"
    Header set Referrer-Policy "{self.random_state.choice(['no-referrer-when-downgrade', 'same-origin', 'strict-origin-when-cross-origin'])}"
    Header set Permissions-Policy "geolocation=(), microphone=(), camera=()"
</IfModule>

# Error documents
ErrorDocument 404 /404.html
ErrorDocument 403 /403.html
ErrorDocument 500 /500.html

# Rewrite rules
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteBase /
    RewriteCond %{{HTTPS}} !=on
    RewriteRule ^(.*)$ https://%{{HTTP_HOST}}/$1 [R=301,L]
    RewriteCond %{{REQUEST_FILENAME}} !-d
    RewriteRule ^(.*)/$ /$1 [L,R=301]
</IfModule>

# Build ID: {self.uniqueness_seed}
"""
        htaccess_path = self.output_dir / ".htaccess"
        with open(htaccess_path, 'w') as f:
            f.write(htaccess_content)
        return htaccess_path

    def generate_manifest_json(self):
        manifest = {
            "name": self.default_domain.replace('.com', '').title(),
            "short_name": self.default_domain[:12],
            "description": f"Social Casino Games - {self.uniqueness_seed}",
            "start_url": "/",
            "display": self.random_state.choice(["standalone", "fullscreen", "minimal-ui"]),
            "background_color": "#000000",
            "theme_color": "#ff0000",
            "orientation": self.random_state.choice(["portrait", "any", "landscape"]),
            "icons": [
                {
                    "src": "/favicon.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable"
                }
            ],
            "id": f"/{self.uniqueness_seed}",
            "scope": "/",
            "lang": "en-US",
            "categories": ["games", "entertainment"],
            "iarc_rating_id": self.uniqueness_seed,
        }
        if self.random_state.random() < 0.5:
            manifest["prefer_related_applications"] = False
            manifest["related_applications"] = []
        if self.random_state.random() < 0.3:
            manifest["dir"] = "ltr"
            manifest["screenshots"] = []
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        return manifest_path

    def generate_complete_website(self, domain_name, site_type="noip"):
        self.log_debug(f"Generating unique website for {domain_name}")
        result = super().generate_complete_website(domain_name, site_type)
        self.log_debug("Adding uniqueness files...")
        robots_path = self.generate_robots_txt()
        htaccess_path = self.generate_htaccess()
        manifest_path = self.generate_manifest_json()
        result['uniqueness_features'] = {
            'seed': self.uniqueness_seed,
            'robots_txt': robots_path,
            'htaccess': htaccess_path,
            'manifest': manifest_path,
            'unique_classes': len(self.unique_classes),
            'unique_ids': len(self.unique_ids),
            'unique_functions': len(self.func_names),
        }
        self.log_debug(f"Website generated with uniqueness seed: {self.uniqueness_seed}")
        return result