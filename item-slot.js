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
    render({ icon = '▫️', rarity = 'normal', quantity = null, tooltip = '', locked = false, enchants = [] }) {
        // Map Japanese/English quality tokens to CSS modifiers
        const rarityMap = {
            bad: 'bad',
            normal: 'common',
            common: 'common',
            good: 'uncommon',
            uncommon: 'uncommon',
            miracle: 'epic',
            epic: 'epic',
            god: 'legendary',
            legendary: 'legendary'
        };
        const rarityClass = rarityMap[rarity] || 'common';

        let fullTooltip = tooltip;
        if (enchants && enchants.length > 0) {
            fullTooltip += '\n【エンチャント】\n' + enchants.map(e => `・${typeof e === 'object' ? (e.name + ' [+' + e.power + ']') : e}`).join('\n');
        }

        const container = this.createElement('div', {
            className: `item-slot item-slot--${rarityClass}${locked ? ' item-slot--locked' : ''}`,
            title: fullTooltip
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

        if (locked) {
            const lockElement = this.createElement('span', {
                className: 'item-slot-lock'
            }, ['🔒']);
            container.appendChild(lockElement);
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
                background-color: var(--colors-surface-surface-mid, #222);
                border: 2px solid var(--colors-surface-border, #444);
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                cursor: pointer;
                transition: transform 0.15s ease, border-color 0.15s ease;
            }
            .item-slot:hover {
                transform: scale(1.08);
                border-color: var(--colors-brand-primary, #5599ff);
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
                font-size: 11px;
                color: #fff;
                background: rgba(0,0,0,0.7);
                padding: 0 3px;
                border-radius: 2px;
                font-family: monospace;
            }
            .item-slot-lock {
                position: absolute;
                top: 2px;
                right: 2px;
                font-size: 11px;
            }
            /* Rarity Borders */
            .item-slot--bad { border-color: #666; opacity: 0.8; }
            .item-slot--common { border-color: var(--colors-surface-border, #555); }
            .item-slot--uncommon { border-color: #38bdf8; }
            .item-slot--rare { border-color: #3b82f6; }
            .item-slot--epic { border-color: #c084fc; box-shadow: 0 0 4px #a855f7; }
            .item-slot--legendary {
                border-color: #fbbf24;
                box-shadow: 0 0 8px #f59e0b;
                animation: slotPulse 1.8s infinite alternate ease-in-out;
            }
            @keyframes slotPulse {
                from { box-shadow: 0 0 4px #d97706; }
                to { box-shadow: 0 0 12px #fbbf24; }
            }
        `;
        document.head.appendChild(style);
    }
}

window.ItemSlot = ItemSlot;
