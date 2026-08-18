/**
 * LogWindow
 * A stateless component for displaying narrative and system messages.
 * Uses design tokens for consistent spacing, typography, and color.
 */
class LogWindow extends UIComponent {
    /**
    /**
     * Render the log window.
     * @param {Object} props
     * @param {Array} props.messages - Array of { text: string, type: 'story'|'combat'|'system'|'warning' }
     * @param {string} [props.id] - Optional element ID
     * @returns {HTMLElement}
     */
    render({ messages = [], id = 'game-log' }) {
        const container = this.createElement('div', {
            id: id,
            className: 'log-window'
        }, []);

        // Add CSS for the log window if not already in global styles
        this._injectStyles();

        messages.forEach(msg => {
            const messageElement = this.createElement('div', {
                className: `log-message log-message--${msg.type || 'story'}`
            }, [msg.text]);
            
            container.appendChild(messageElement);
        });

        return container;
    }

    /**
     * Inject component-specific styles that reference design tokens.
     */
    _injectStyles() {
        if (document.getElementById('log-window-styles')) return;

        const style = document.createElement('style');
        style.id = 'log-window-styles';
        style.textContent = `
            .log-window {
                background-color: var(--colors-surface-surface-low);
                border: 1px solid var(--colors-surface-border);
                border-radius: 8px;
                padding: var(--spacing-4);
                font-family: var(--typography-font-family-main);
                font-size: var(--typography-size-body);
                color: var(--colors-content-text-main);
                display: flex;
                flex-direction: column;
                gap: var(--spacing-2);
                max-height: 300px;
                overflow-y: auto;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            }
            .log-message {
                padding: var(--spacing-1) var(--spacing-2);
                border-radius: 4px;
                animation: logFadeIn var(--motion-duration-standard) var(--motion-easing-smooth);
                line-height: 1.5;
            }
            .log-message--story { 
                color: var(--colors-content-text-main); 
            }
            .log-message--combat { 
                color: var(--colors-status-danger); 
                font-weight: var(--typography-weight-medium);
            }
            .log-message--system { 
                color: var(--colors-brand-primary); 
                font-style: italic;
            }
            .log-message--warning { 
                color: var(--colors-status-warning); 
                background: rgba(234, 179, 8, 0.1);
            }
            @keyframes logFadeIn {
                from { opacity: 0; transform: translateY(5px); }
                to { opacity: 1; transform: translateY(0); }
            }
        `;
        document.head.appendChild(style);
    }
}

window.LogWindow = LogWindow;
