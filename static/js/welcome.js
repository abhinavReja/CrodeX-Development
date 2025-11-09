/**
 * Welcome Screen Handler
 * Shows welcome screen with logo animation on first page load
 */

(function() {
    'use strict';

    const WELCOME_SHOWN_KEY = 'crodex_welcome_shown';
    const WELCOME_DURATION = 2500; // 2.5 seconds - original timing
    const TRANSITION_DURATION = 1000; // 1 second - original smooth transition

    /**
     * Initialize welcome screen
     */
    function initWelcomeScreen() {
        const welcomeScreen = document.getElementById('welcome-screen');
        const welcomeLogo = document.getElementById('welcome-logo');
        const navBrand = document.getElementById('nav-brand');
        const body = document.body;

        // Check if welcome screen has been shown before
        const welcomeShown = localStorage.getItem(WELCOME_SHOWN_KEY);

        if (welcomeShown === 'true') {
            // Welcome screen already shown, hide it immediately
            if (welcomeScreen) {
                welcomeScreen.classList.add('hidden');
            }
            if (navBrand) {
                navBrand.classList.add('visible');
                navBrand.style.opacity = '1';
                navBrand.style.visibility = 'visible';
            }
            body.classList.remove('welcome-active');
            return;
        }

        // First time visit - show welcome screen
        if (welcomeScreen && welcomeLogo && navBrand) {
            // Add welcome-active class to body (this will hide navbar logo via CSS)
            body.classList.add('welcome-active');
            
            // Ensure navbar logo is initially hidden
            navBrand.classList.remove('visible');
            navBrand.style.opacity = '0';
            navBrand.style.visibility = 'visible'; // Keep visible for measurements

            // Wait for welcome duration, then start transition
            requestAnimationFrame(() => {
                setTimeout(() => {
                    startLogoTransition(welcomeScreen, welcomeLogo, navBrand, body);
                }, WELCOME_DURATION);
            });
        }
    }

    /**
     * Start logo transition from welcome screen to navbar
     * Logo smoothly resizes and moves to navbar position without disappearing
     */
    function startLogoTransition(welcomeScreen, welcomeLogo, navBrand, body) {
        // Ensure navbar is visible but transparent for accurate measurements
        navBrand.style.visibility = 'visible';
        navBrand.style.opacity = '0';
        
        // Wait for layout to stabilize
        requestAnimationFrame(() => {
            // Get current positions
            const welcomeLogoRect = welcomeLogo.getBoundingClientRect();
            const navBrandRect = navBrand.getBoundingClientRect();

            // Calculate exact scale to match navbar logo size
            const navBrandWidth = navBrandRect.width;
            const navBrandHeight = navBrandRect.height;
            const scaleX = navBrandWidth / welcomeLogoRect.width;
            const scaleY = navBrandHeight / welcomeLogoRect.height;
            const scale = Math.min(scaleX, scaleY) * 0.9; // Adjust for perfect visual alignment

            // Calculate translation to align centers
            const startX = welcomeLogoRect.left + (welcomeLogoRect.width / 2);
            const startY = welcomeLogoRect.top + (welcomeLogoRect.height / 2);
            const endX = navBrandRect.left + (navBrandRect.width / 2);
            const endY = navBrandRect.top + (navBrandRect.height / 2);
            
            const translateX = endX - startX;
            const translateY = endY - startY;

            // Prepare welcome logo for smooth transition
            welcomeLogo.classList.add('transitioning');
            welcomeLogo.style.transformOrigin = 'center center';
            welcomeLogo.style.willChange = 'transform';
            welcomeLogo.style.opacity = '1'; // Keep fully visible during transition
            
            // Set transition - original smooth timing
            welcomeLogo.style.transition = `transform ${TRANSITION_DURATION}ms cubic-bezier(0.4, 0, 0.2, 1)`;
            
            // Start the animation - logo moves and scales continuously
            requestAnimationFrame(() => {
                welcomeLogo.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
            });

            // Don't fade background until logo is well into its transition
            // Wait until 70% of transition is complete so user can see the movement
            setTimeout(() => {
                welcomeScreen.classList.add('hiding');
            }, TRANSITION_DURATION * 0.7); // Start fading background at 70% of transition

            // Seamless handoff: When logo is ~95% in position, switch to navbar logo
            setTimeout(() => {
                // Show navbar logo exactly when welcome logo reaches final position
                navBrand.classList.add('visible');
                navBrand.style.opacity = '1';
                
                // Hide welcome logo after navbar logo appears for seamless handoff
                setTimeout(() => {
                    welcomeLogo.style.transition = `transform ${TRANSITION_DURATION}ms cubic-bezier(0.4, 0, 0.2, 1), opacity 0.05s ease-out`;
                    welcomeLogo.style.opacity = '0';
                }, 50); // Small delay for perfect handoff
            }, TRANSITION_DURATION - 50); // At 95% - logo is nearly in final position

            // Clean up after transition completes
            setTimeout(() => {
                welcomeScreen.classList.add('hidden');
                welcomeLogo.classList.remove('transitioning');
                welcomeLogo.style.transform = '';
                welcomeLogo.style.opacity = '';
                welcomeLogo.style.transformOrigin = '';
                welcomeLogo.style.willChange = '';
                welcomeLogo.style.transition = '';
                body.classList.remove('welcome-active');
                
                // Mark welcome screen as shown
                localStorage.setItem(WELCOME_SHOWN_KEY, 'true');
            }, TRANSITION_DURATION + 100); // Cleanup after transition completes
        });
    }

    /**
     * Reset welcome screen (for testing purposes)
     * Can be called from browser console: resetWelcomeScreen()
     */
    window.resetWelcomeScreen = function() {
        localStorage.removeItem(WELCOME_SHOWN_KEY);
        location.reload();
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWelcomeScreen);
    } else {
        initWelcomeScreen();
    }
})();
