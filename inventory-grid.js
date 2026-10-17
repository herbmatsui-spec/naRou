/**
 * InventoryGrid
 * A stateless component that renders a grid of ItemSlots.
 * Handles the layout and dynamic generation of items.
 */
class InventoryGrid extends UIComponent {
    /**
     * Render the inventory grid.
     * @param {Object} props
     * @param {Array} props.items - Array of item objects: { icon, rarity, quantity, tooltip }
     * @param {number} [props.columns=5] - Number of columns in the grid
     * @param {string} [props.id] - Optional element ID
     * @returns {HTMLElement}
     */
    render({ items = [], columns = 5, id = 'inventory-grid' }) {
        const container = this.createElement('div', {
            id: id,
            className: 'inventory-grid'
        }, []);

        // Set grid columns dynamically
        container.style.setProperty('--grid-cols', columns);

        const slotComponent = new ItemSlot();

        items.forEach(item => {
            const slot = slotComponent.render({
                icon: item.icon,
                rarity: item.rarity,
                quantity: item.quantity,
                tooltip: item.tooltip
            });
            container.appendChild(slot);
        });

        this._injectStyles();

        return container;
    }

    _injectStyles() {
        if (document.getElementById('inventory-grid-styles')) return;

        const style = document.createElement('style');
        style.id = 'inventory-grid-styles';
        style.textContent = `
            .inventory-grid {
                display: grid;
                grid-template-columns: repeat(var(--grid-cols, 5), 1fr);
                gap: var(--spacing-2);
                padding: var(--spacing-4);
                background-color: var(--colors-surface-surface-low);
                border: 1px solid var(--colors-surface-border);
                border-radius: 8px;
                width: fit-content;
                max-width: 100%;
                overflow-x: auto;
            }
        `;
        document.head.appendChild(style);
    }
}

window.InventoryGrid = InventoryGrid;
