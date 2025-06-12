<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>15 Coins Grand Gold Edition - Jonsslots</title>
    <link rel="canonical" href="https://jonsslots.com/games/15-coins-grand-gold-edition" />
    <link rel="icon" type="image/png" href="favicon.png">
    <!-- Load Font properly -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" integrity="sha512-iecdLmaskl7CVkqkXNQ/ZH/XLlvWZOJyj7Yy7tcenmpD1ypASozpmT/E0iPtmFIB46ZmdtAc9eNBvH0H/ZpiBw==" crossorigin="anonymous" referrerpolicy="no-referrer">
    <link rel="stylesheet" href="../assets/css/base.css">
    <link rel="stylesheet" href="../assets/css/game.css">
</head>
<body>
    <!-- Sidebar -->
    <nav class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <div class="logo">Jonsslots</div>
        </div>
        <div class="sidebar-nav">
            <a href="/" class="nav-item">
                <i class="fas fa-home"></i> <span>Home</span>
            </a>
            <a href="/games" class="nav-item">
                <i class="fas fa-gamepad"></i> <span>Games</span>
            </a>
            <a href="/pages/about/" class="nav-item">
                <i class="fas fa-info-circle"></i> <span>About Us</span>
            </a>
            <a href="/pages/contact/" class="nav-item">
                <i class="fas fa-envelope"></i> <span>Contact Us</span>
            </a>
        </div>
        <button class="sidebar-toggle" onclick="toggleSidebar()" aria-label="Toggle sidebar">
            <i class="fas fa-chevron-left"></i>
        </button>
    </nav>

    <!-- Mobile Sidebar Toggle -->
    <button class="mobile-sidebar-toggle" onclick="toggleMobileSidebar()" id="mobileSidebarToggle" aria-label="Open menu">
        <i class="fas fa-bars"></i>
    </button>

    <!-- Sidebar Overlay for Mobile -->
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="closeMobileSidebar()"></div>

    <!-- Main Wrapper -->
    <main class="main-wrapper" id="mainWrapper">

        <!-- Game Header -->
        <section class="game-header">
            <div class="game-header-content">
                <nav class="breadcrumb">
                    <a href="/">Home</a>
                    <span class="breadcrumb-separator">/</span>
                    <a href="/games">Games</a>
                    <span class="breadcrumb-separator">/</span>
                    <span>15 Coins Grand Gold Edition</span>
                </nav>
                
                <h1 class="game-title">15 Coins Grand Gold Edition</h1>
            </div>
        </section>

        <!-- Game Container -->
        <section class="game-container">
            <div class="game-wrapper">
                <div class="game-iframe-container">
                    <div class="game-loading" id="gameLoading">
                        <div class="game-loading-spinner"></div>
                        <p>Loading 15 Coins Grand Gold Edition...</p>
                    </div>
                    
                    <iframe 
                        id="gameIframe"
                        class="game-iframe" 
                        src="https://slotslaunch.com/iframe/19764?token=6neGxBm3O8L6Wy2ZbD0xykkFwtaDi653SH7RanMSLtEPDE1V5f"
                        title="15 Coins Grand Gold Edition"
                        allowfullscreen
                        onload="hideLoading()"
                        onerror="showError()">
                    </iframe>
                    
                    <button class="fullscreen-btn" onclick="toggleFullscreen()" aria-label="Toggle fullscreen">
                        <i class="fas fa-expand"></i>
                    </button>
                </div>
            </div>
        </section>

        <!-- Footer -->
        <footer class="footer">
            <div class="footer-content">
                <div class="footer-links">
                    <a href="/pages/terms/" class="footer-link">Terms & Conditions</a>
                    <a href="/pages/privacy/" class="footer-link">Privacy Policy</a>
                    <a href="/pages/cookies/" class="footer-link">Cookie Policy</a>
                    <a href="/pages/responsible/" class="footer-link">Responsible Social Gaming</a>
                </div>
                <div class="footer-bottom">
                    <p><strong>Disclaimer:</strong> The domain (jonsslots.com) is a website designed solely for entertainment purposes where users can play games without risking any real money. It does not involve any form of 'real-money gambling' or provide chances to earn actual money based on gameplay.</p>
                    <p>&copy; 2025 jonsslots.com. All rights reserved.</p>
                </div>
            </div>
        </footer>
    </main>
    <script src="../assets/js/base.js"></script>
    <script src="../assets/js/game.js"></script>
</body>
</html>