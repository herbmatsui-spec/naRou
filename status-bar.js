/**
 * StatusBar
 * A stateless component for displaying numeric gauges (HP, MP, EXP, etc.)
 * Uses design tokens for coloring and sizing.
 */
class StatusBar extends UIComponent {
    /**
     * Render the status bar with optional status effect badges.
     * @param {Object} props
     * @param {string} props.label - Label text (e.g., "HP")
     * @param {number} props.current - Current value
     * @param {number} props.max - Maximum value
     * @param {string} [props.colorToken] - CSS variable for the bar color (e.g., '--colors-status-danger')
     * @param {Array} [props.statusBadges] - Array of active status objects: { type, icon, label, duration }
     * @param {string} [props.id] - Optional element ID
     * @returns {HTMLElement}
     */
    render({ label, current, max, colorToken = '--colors-brand-primary', statusBadges = [], id = 'status-bar' }) {
        const percentage = Math.min(Math.max((current / max) * 100, 0), 100);

        const container = this.createElement('div', {
            id: id,
            className: 'status-bar-container'
        }, []);

        const labelElement = this.createElement('span', {
            className: 'status-bar-label'
        }, [label]);

        const track = this.createElement('div', {
            className: 'status-bar-track'
        }, []);

        const fill = this.createElement('div', {
            className: 'status-bar-fill',
            style: `width: ${percentage}%; background-color: var(${colorToken}, #3b82f6);`
        }, []);

        const valueText = this.createElement('span', {
            className: 'status-bar-value'
        }, [`${current}/${max}`]);

        track.appendChild(fill);
        container.appendChild(labelElement);
        container.appendChild(track);
        container.appendChild(valueText);

        // Status Effect Badges (Step 65)
        if (statusBadges && statusBadges.length > 0) {
            const badgeContainer = this.createElement('div', {
                className: 'status-badges-container'
            }, []);

            statusBadges.forEach(b => {
                const badge = this.createElement('span', {
                    className: `status-badge status-badge--${b.type}`,
                    title: `${b.label || b.type}${b.duration ? ` (残り${b.duration}ターン)` : ''}`
                }, [b.icon || '⚠️']);
                badgeContainer.appendChild(badge);
            });
            container.appendChild(badgeContainer);
        }

        this._injectStyles();

        return container;
    }

    _injectStyles() {
        if (document.getElementById('status-bar-styles')) return;

        const style = document.createElement('style');
        style.id = 'status-bar-styles';
        style.textContent = `
            .status-bar-container {
                display: flex;
                align-items: center;
                gap: var(--spacing-2);
                width: 100%;
                max-width: 300px;
                font-family: var(--typography-font-family-main);
            }
            .status-bar-label {
                font-size: var(--typography-size-caption);
                font-weight: var(--typography-weight-bold);
                color: var(--colors-content-text-muted);
                min-width: 30px;
            }
            .status-bar-track {
                flex-grow: 1;
                height: 12px;
                background-color: var(--colors-surface-surface-mid);
                border: 1px solid var(--colors-surface-border);
                border-radius: 6px;
                overflow: hidden;
                position: relative;
            }
            .status-bar-fill {
                height: 100%;
                transition: width var(--motion-duration-standard) var(--motion-easing-smooth);
                box-shadow: inset 0 1px 2px rgba(255,255,255,0.2);
            }
            .status-bar-value {
                font-size: var(--typography-size-caption);
                font-family: monospace;
                color: var(--colors-content-text-main);
                min-width: 60px;
                text-align: right;
            }
            .status-badges-container {
                display: flex;
                gap: 4px;
                margin-left: 6px;
            }
            .status-badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                padding: 1px 3px;
                border-radius: 4px;
                background: rgba(0,0,0,0.5);
                border: 1px solid rgba(255,255,255,0.2);
                cursor: help;
                animation: badgePulse 2s infinite ease-in-out;
            }
            .status-badge--poison { border-color: #22c55e; background: rgba(34,197,94,0.2); }
            .status-badge--burn { border-color: #ef4444; background: rgba(239,68,68,0.2); }
            .status-badge--freeze { border-color: #38bdf8; background: rgba(56,189,248,0.2); }
            .status-badge--paralyze { border-color: #eab308; background: rgba(234,179,8,0.2); }
            @keyframes badgePulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.15); }
            }
        `;
        document.head.appendChild(style);
    }
}

window.StatusBar = StatusBar;
