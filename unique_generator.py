import random
import hashlib
from app import CompleteWebsiteGenerator

class UniqueWebsiteGenerator(CompleteWebsiteGenerator):
    """
    Website generator with advanced uniqueness features:
    - Dynamic class/ID mapping
    - Unique CSS/JS/image/config variations
    - HTML structure and attribute randomization
    """
    def __init__(self, openai_api_key, default_domain="spikeup.com", uniqueness_seed=None):
        super().__init__(openai_api_key, default_domain)
        # Use a seed for reproducibility per site/domain
        if uniqueness_seed is None:
            uniqueness_seed = hashlib.sha256(default_domain.encode()).hexdigest()[:8]
        self.uniqueness_seed = uniqueness_seed
        self.random_state = random.Random(self.uniqueness_seed)
        self._class_map = {}
        self._id_map = {}
        self._css_var_map = {}
        self.class_pools = {
            "sidebar": ["main-sidebar", "side-nav-menu", "navigation-panel", "sidebar-" + self.uniqueness_seed],
            "sidebar-header": ["sidebar-header", "nav-header", "panel-header", "header-" + self.uniqueness_seed],
            "logo": ["logo", "brand-logo", "site-logo", "logo-" + self.uniqueness_seed],
            "sidebar-nav": ["sidebar-nav", "nav-list", "side-menu", "nav-" + self.uniqueness_seed],
            "nav-item": ["nav-item", "menu-link", "side-link", "item-" + self.uniqueness_seed],
            "sidebar-toggle": ["sidebar-toggle", "toggle-btn", "side-toggle", "toggle-" + self.uniqueness_seed],
            "main-wrapper": ["main-wrapper", "content-wrapper", "main-content", "wrapper-" + self.uniqueness_seed],
            # Add more as needed
        }
        self.id_pools = {
            "sidebar": ["sidebar", "navSidebar", "sidePanel", "sb-" + self.uniqueness_seed],
            "mainWrapper": ["mainWrapper", "contentWrap", "mainWrap", "mw-" + self.uniqueness_seed],
            # Add more as needed
        }
        self.element_tag_pools = {
            "wrapper": ["div", "section", "article"],
            "sidebar": ["nav", "aside", "div"],
            "main": ["main", "section", "div"],
            # Add more as needed
        }
        self.css_var_bases = {
            "spacing": ["--primary-spacing", "--core-space-unit"],
            "timing": ["--transition-normal", "--speed-default"],
            "shadow": ["--shadow-blur", "--blur-amount"],
        }

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

    def get_element_tag(self, key):
        pool = self.element_tag_pools.get(key, ["div"])
        return self.random_state.choice(pool)

    def random_inline_style(self, key, base_styles):
        # base_styles: dict of {css_prop: base_value}
        style_strs = []
        for prop, base in base_styles.items():
            if isinstance(base, (int, float)):
                # Micro-variation: ±2%
                delta = base * self.random_state.uniform(-0.02, 0.02)
                value = base + delta
                if "px" in prop or "padding" in prop or "margin" in prop:
                    style_strs.append(f"{prop}: {value:.2f}px")
                else:
                    style_strs.append(f"{prop}: {value}")
            elif isinstance(base, str) and base.endswith("px"):
                num = float(base[:-2])
                delta = num * self.random_state.uniform(-0.02, 0.02)
                value = num + delta
                style_strs.append(f"{prop}: {value:.2f}px")
            else:
                style_strs.append(f"{prop}: {base}")
        return "; ".join(style_strs)

    @property
    def unique_css_vars(self):
        if not self._css_var_map:
            for key, bases in self.css_var_bases.items():
                var_name = self.random_state.choice(bases) + "-" + self.uniqueness_seed
                if key == "spacing":
                    value = f"{1 + self.random_state.uniform(-0.05, 0.05):.2f}rem"
                elif key == "timing":
                    value = f"{0.3 + self.random_state.uniform(-0.05, 0.05):.2f}s"
                elif key == "shadow":
                    value = f"{4 + self.random_state.uniform(-0.5, 0.5):.1f}px"
                else:
                    value = self.uniqueness_seed
                self._css_var_map[var_name] = value
        return self._css_var_map

    def get_uniqueness_seed(self):
        return self.uniqueness_seed

    def randomize_image_filename(self, filename):
        # filename: e.g. "slotgame.jpg"
        name, ext = filename.rsplit('.', 1)
        hash_prefix = self.uniqueness_seed
        hash_suffix = hashlib.md5(filename.encode()).hexdigest()[:6]
        formats = ["jpg", "jpeg", "webp", "png"]
        new_ext = self.random_state.choice(formats)
        pattern = self.random_state.choice([
            f"{hash_prefix}-{name}.{new_ext}",
            f"{name}-{hash_suffix}.{new_ext}",
            f"{name}-{int(self.random_state.random()*1e5)}.{new_ext}",
        ])
        return pattern