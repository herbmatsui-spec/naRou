/**
 * ItemSlot
 * A stateless component for displaying a single item slot.
 * Visuals are driven by rarity tokens and design-tokens.json.
 */
class ItemSlot extends UIComponent {
    /**
     * Render the item slot.
     * @param {Object} props
     * @param {string} [props.icon] - Emoji or icon path
     * @param {string} [props.rarity] - 'common'|'uncommon'|'rare'|'epic'|'legendary'
     * @param {number} [props.quantity] - Item count
     * @param {string} [props.tooltip] - Tooltip text
     * @returns {HTMLElement}
     */
    render({ icon = '▫️', rarity = 'common', quantity = null, tooltip = '' }) {
        const container = this.createElement('div', {
            className: `item-slot item-slot--${rarity}`,
            title: tooltip
        }, []);

        const iconElement = this.createElement('span', {
            className: 'item-slot-icon'
        }, [icon]);

        if (quantity && quantity > 1) {
            const qtyElement = this.createElement('span', {
                className: 'item-slot-quantity'
            }, [`x${quantity}`]);
            container.appendChild(qtyElement);
        }

        container.appendChild(iconElement);
        this._injectStyles();

        return container;
    }

    _injectStyles() {
        if (document.getElementById('item-slot-styles')) return;

        const style = document.createElement('style');
        style.id = 'item-slot-styles';
        style.textContent = `
            .item-slot {
                width: 48px;
                height: 48px;
                background-color: var(--colors-surface-surface-mid);
                border: 2px solid var(--colors-surface-border);
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                cursor: pointer;
                transition: transform var(--motion-duration-fast) var(--motion-easing-smooth),
                                border-color var(--motion-duration-fast) var(--motion-easing-smooth);
            }
            .item-slot:hover {
                transform: scale(1.1);
                border-color: var(--colors-brand-primary);
                z-index: 10;
            }
            .item-slot-icon {
                font-size: 24px;
                user-select: none;
            }
            .item-slot-quantity {
                position: absolute;
                bottom: 2px;
                right: 2px;
                font-size: var(--typography-size-tiny);
                color: var(--colors-content-text-main);
                background: rgba(0,0,0,0.6);
                padding: 0 2px;
                border-radius: 2px;
                font-family: monospace;
            }
            /* Rarity Borders */
            .item-slot--common { border-color: var(--colors-surface-border); }
            .item-slot--uncommon { border-color: var(--colors-status-success); }
            .item-slot--rare { border-color: var(--colors-brand-primary); }
            .item-slot--epic { border-color: var(--colors-brand-secondary); }
            .item-slot--legendary {
                border-color: var(--colors-brand-accent);
                box-shadow: 0 0 8px var(--colors-brand-accent);
                animation: slotPulse var(--motion-duration-slow) infinite alternate ease-in-out;
            }
            @keyframes slotPulse {
                from { box-shadow: 0 0 4px var(--colors-brand-accent); }
                to { box-shadow: 0 0 12px var(--colors-brand-accent); }
            }
        `;
        document.head.appendChild(style);
    }
}

window.ItemSlot = ItemSlot;
