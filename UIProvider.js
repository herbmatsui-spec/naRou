/**
 * UIProvider
 * Handles the bridge between design-tokens.json and the browser CSS.
 * It transforms JSON tokens into CSS Custom Properties (--token-name)
 * and injects them into the :root element.
 */
class UIProvider {
    constructor(tokensPath = 'design-tokens.json') {
        this.tokensPath = tokensPath;
        this.tokens = null;
    }

    /**
     * Load tokens from JSON and apply them to the document root.
     */
    async init() {
        try {
            const response = await fetch(this.tokensPath);
            if (!response.ok) throw new Error(`Failed to load tokens: ${response.statusText}`);
            this.tokens = await response.json();
            this.applyTokens();
            console.log('🎨 UIProvider: Design tokens applied successfully.');
        } catch (error) {
            console.error('❌ UIProvider Error:', error);
            this.applyFallbacks();
        }
    }

    /**
     * Flattens the nested JSON tokens and injects them as CSS variables.
     */
    applyTokens() {
        const root = document.documentElement;
        const cssVars = {};

        // Recursively flatten tokens: { colors: { brand: { primary: '#...' } } } -> { '--colors-brand-primary': '#...' }
        const flatten = (obj, prefix = '') => {
            for (const [key, value] of Object.entries(obj)) {
                const newKey = prefix ? `${prefix}-${key}` : `--${key}`;
                if (typeof value === 'object' && value !== null) {
                    flatten(value, newKey);
                } else {
                    cssVars[newKey] = value;
                }
            }
        };

        flatten(this.tokens);

        // Apply all variables to :root
        Object.entries(cssVars).forEach(([prop, val]) => {
            root.style.setProperty(prop, val);
        });
    }

    /**
     * Minimal fallback styles to prevent total UI collapse if JSON fails to load.
     */
    applyFallbacks() {
        console.warn('⚠️ UIProvider: Applying emergency fallback styles.');
        const root = document.documentElement;
        const fallbacks = {
            '--colors-brand-primary': '#38bdf8',
            '--colors-surface-background': '#070913',
            '--colors-content-text-main': '#ffffff',
            '--spacing-4': '16px'
        };
        Object.entries(fallbacks).forEach(([prop, val]) => {
            root.style.setProperty(prop, val);
        });
    }

    /**
     * Helper to get a token value directly in JS.
     */
    getToken(path) {
        return path.split('.').reduce((acc, part) => acc && acc[part], this.tokens);
    }
}

// Export as a singleton for global use across demos
window.UIProvider = new UIProvider();
