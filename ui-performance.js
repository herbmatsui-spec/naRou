/**
 * UIPerformanceOptimizer
 * Provides utilities to minimize DOM thrashing and optimize
 * the rendering of the UI Design System.
 */
class UIPerformanceOptimizer {
    /**
     * Batch updates to the DOM to avoid multiple reflows.
     * @param {Function} updateFn - Function containing multiple DOM operations.
     */
    static batchUpdate(updateFn) {
        requestAnimationFrame(() => {
            updateFn();
        });
    }

    /**
     * Optimized element creation for large grids (like Inventory).
     * Uses DocumentFragment to reduce layout shifts.
     * @param {Array} elements - Array of HTMLElements.
     * @returns {DocumentFragment}
     */
    static createFragment(elements) {
        const fragment = document.createDocumentFragment();
        elements.forEach(el => fragment.appendChild(el));
        return fragment;
    }

    /**
     * Debounce function to prevent excessive UI updates during
     * window resizing or rapid state changes.
     */
    static debounce(fn, delay = 100) {
        let timeoutId;
        return (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };
    }
}

window.UIPerformanceOptimizer = UIPerformanceOptimizer;

// Enhance InventoryGrid to use batch updates and fragments
if (window.InventoryGrid) {
    const originalRender = window.InventoryGrid.prototype.render;
    window.InventoryGrid.prototype.render = function({ items = [], ...props }) {
        const container = this.createElement('div', {
            className: 'inventory-grid',
            id: props.id || 'inventory-grid'
        }, []);

        container.style.setProperty('--grid-cols', props.columns || 5);

        const slotComponent = new ItemSlot();
        const slots = items.map(item => slotComponent.render({
            icon: item.icon,
            rarity: item.rarity,
            quantity: item.quantity,
            tooltip: item.tooltip
        }));

        container.appendChild(UIPerformanceOptimizer.createFragment(slots));
        this._injectStyles();

        return container;
    };
}
