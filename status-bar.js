/**
 * StatusBar
 * A stateless component for displaying numeric gauges (HP, MP, EXP, etc.)
 * Uses design tokens for coloring and sizing.
 */
class StatusBar extends UIComponent {
    /**
     * Render the status bar.
     * @param {Object} props
     * @param {string} props.label - Label text (e.g., "HP")
     * @param {number} props.current - Current value
     * @param {number} props.max - Maximum value
     * @param {string} [props.colorToken] - CSS variable for the bar color (e.g., '--colors-status-danger')
     * @param {string} [props.id] - Optional element ID
     * @returns {HTMLElement}
     */
    render({ label, current, max, colorToken = '--colors-brand-primary', id = 'status-bar' }) {
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
            style: `width: ${percentage}%; background-color: var(${colorToken});`
        }, []);

        const valueText = this.createElement('span', {
            className: 'status-bar-value'
        }, [`${current}/${max}`]);

        track.appendChild(fill);
        container.appendChild(labelElement);
        container.appendChild(track);
        container.appendChild(valueText);

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
        `;
        document.head.appendChild(style);
    }
}

window.StatusBar = StatusBar;
