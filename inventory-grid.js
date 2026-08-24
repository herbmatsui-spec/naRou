/**
 * InventoryGrid
 * A rich interactive component for inventory management.
 * Features: Category Filtering, Multiple Sorting options, Lock protection, and Pagination.
 * (Steps 25-44)
 */
class InventoryGrid extends UIComponent {
    constructor() {
        super();
        this.currentFilter = 'all';
        this.currentSort = 'default';
        this.currentPage = 1;
        this.pageSize = 20;
    }

    /**
     * Render the inventory grid with interactive toolbar and pagination.
     * @param {Object} props
     * @param {Array} props.items - Array of item objects: { id, name, category, icon, rarity, quantity, tooltip, weight, value, locked, enchants }
     * @param {number} [props.columns=5] - Number of columns in the grid
     * @param {string} [props.id] - Optional element ID
     * @param {Function} [props.onItemClick] - Callback when an item slot is clicked
     * @param {Function} [props.onItemLockToggle] - Callback when an item lock is toggled
     * @returns {HTMLElement}
     */
    render({ items = [], columns = 5, id = 'inventory-grid-container', onItemClick = null, onItemLockToggle = null }) {
        this.allItems = items;
        this.columns = columns;
        this.onItemClick = onItemClick;
        this.onItemLockToggle = onItemLockToggle;

        const root = this.createElement('div', {
            id: id,
            className: 'inventory-system-wrapper'
        }, []);

        // 1. Toolbar (Filter tabs & Sort dropdown) (Steps 27, 28)
        const toolbar = this._createToolbar();
        root.appendChild(toolbar);

        // 2. Grid Container
        const grid = this.createElement('div', {
            id: `${id}-grid`,
            className: 'inventory-grid'
        }, []);
        grid.style.setProperty('--grid-cols', columns);
        root.appendChild(grid);

        // 3. Pagination bar (Steps 41-43)
        const pagination = this._createPaginationBar();
        root.appendChild(pagination);

        this.rootElement = root;
        this.gridElement = grid;
        this.paginationElement = pagination;

        this._injectStyles();
        this._updateView();

        return root;
    }

    _createToolbar() {
        const toolbar = this.createElement('div', { className: 'inventory-toolbar' }, []);

        // Filter Tabs (Step 27)
        const filterGroup = this.createElement('div', { className: 'inventory-filter-group' }, []);
        const filters = [
            { id: 'all', label: 'すべて' },
            { id: 'weapon', label: '武器' },
            { id: 'armor', label: '防具' },
            { id: 'consumable', label: '消耗品' },
            { id: 'valuable', label: '貴重品' },
        ];

        filters.forEach(f => {
            const btn = this.createElement('button', {
                className: `inventory-tab-btn ${this.currentFilter === f.id ? 'active' : ''}`,
                innerText: f.label
            }, []);
            btn.addEventListener('click', () => {
                this.currentFilter = f.id;
                this.currentPage = 1;
                this.rootElement.querySelectorAll('.inventory-tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this._updateView();
            });
            filterGroup.appendChild(btn);
        });
        toolbar.appendChild(filterGroup);

        // Sort Selector (Step 28)
        const sortGroup = this.createElement('div', { className: 'inventory-sort-group' }, []);
        const sortLabel = this.createElement('span', { className: 'inventory-sort-label', innerText: '並び順: ' }, []);
        const sortSelect = this.createElement('select', { className: 'inventory-sort-select' }, []);

        const sortOptions = [
            { id: 'default', label: '入手順' },
            { id: 'name', label: '名前順' },
            { id: 'quality', label: '品質 (レア度) 順' },
            { id: 'value', label: '価値の高い順' },
            { id: 'weight', label: '重量順' },
        ];

        sortOptions.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.id;
            option.textContent = opt.label;
            if (this.currentSort === opt.id) option.selected = true;
            sortSelect.appendChild(option);
        });

        sortSelect.addEventListener('change', (e) => {
            this.currentSort = e.target.value;
            this._updateView();
        });

        sortGroup.appendChild(sortLabel);
        sortGroup.appendChild(sortSelect);
        toolbar.appendChild(sortGroup);

        return toolbar;
    }

    _createPaginationBar() {
        const bar = this.createElement('div', { className: 'inventory-pagination' }, []);

        const prevBtn = this.createElement('button', {
            className: 'pagination-btn prev-btn',
            innerText: '◀ 前へ'
        }, []);
        prevBtn.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this._updateView();
            }
        });

        const pageIndicator = this.createElement('span', {
            className: 'pagination-indicator',
            innerText: '1 / 1'
        }, []);

        const nextBtn = this.createElement('button', {
            className: 'pagination-btn next-btn',
            innerText: '次へ ▶'
        }, []);
        nextBtn.addEventListener('click', () => {
            const totalPages = Math.ceil(this._getFilteredAndSortedItems().length / this.pageSize) || 1;
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this._updateView();
            }
        });

        bar.appendChild(prevBtn);
        bar.appendChild(pageIndicator);
        bar.appendChild(nextBtn);

        this.pageIndicator = pageIndicator;
        this.prevBtn = prevBtn;
        this.nextBtn = nextBtn;

        return bar;
    }

    _getFilteredAndSortedItems() {
        let list = [...(this.allItems || [])];

        // 1. Filter (Step 30)
        if (this.currentFilter !== 'all') {
            if (this.currentFilter === 'weapon') {
                list = list.filter(i => i.category === 'weapon');
            } else if (this.currentFilter === 'armor') {
                list = list.filter(i => ['armor', 'shield', 'helm', 'ring'].includes(i.category));
            } else if (this.currentFilter === 'consumable') {
                list = list.filter(i => ['potion', 'scroll', 'food', 'spellbook'].includes(i.category));
            } else if (this.currentFilter === 'valuable') {
                list = list.filter(i => ['ore', 'gold'].includes(i.category) || ['miracle', 'god', 'epic', 'legendary'].includes(i.rarity));
            }
        }

        // 2. Sort (Step 31-34)
        const qualityRank = { bad: 0, common: 1, normal: 1, good: 2, uncommon: 2, miracle: 3, epic: 3, god: 4, legendary: 4 };

        if (this.currentSort === 'name') {
            list.sort((a, b) => (a.name || '').localeCompare(b.name || '', 'ja'));
        } else if (this.currentSort === 'value') {
            list.sort((a, b) => (b.value || 0) - (a.value || 0));
        } else if (this.currentSort === 'weight') {
            list.sort((a, b) => (a.weight || 0) - (b.weight || 0));
        } else if (this.currentSort === 'quality') {
            list.sort((a, b) => (qualityRank[b.rarity] || 1) - (qualityRank[a.rarity] || 1));
        }

        // Step 39: Locked items are pinned to the top
        list.sort((a, b) => (b.locked ? 1 : 0) - (a.locked ? 1 : 0));

        return list;
    }

    _updateView() {
        if (!this.gridElement) return;

        const filtered = this._getFilteredAndSortedItems();
        const totalPages = Math.ceil(filtered.length / this.pageSize) || 1;

        if (this.currentPage > totalPages) this.currentPage = totalPages;
        if (this.currentPage < 1) this.currentPage = 1;

        // Update pagination indicator
        if (this.pageIndicator) {
            this.pageIndicator.innerText = `${this.currentPage} / ${totalPages} (${filtered.length}件)`;
            this.prevBtn.disabled = this.currentPage <= 1;
            this.nextBtn.disabled = this.currentPage >= totalPages;
        }

        // Slice items for current page
        const startIdx = (this.currentPage - 1) * this.pageSize;
        const pageItems = filtered.slice(startIdx, startIdx + this.pageSize);

        // Clear grid
        this.gridElement.innerHTML = '';

        if (pageItems.length === 0) {
            const emptyMsg = this.createElement('div', {
                className: 'inventory-empty-msg',
                innerText: 'アイテムがありません'
            }, []);
            this.gridElement.appendChild(emptyMsg);
            return;
        }

        const slotComponent = new ItemSlot();
        pageItems.forEach(item => {
            const slot = slotComponent.render({
                icon: item.icon,
                rarity: item.rarity,
                quantity: item.quantity,
                tooltip: item.tooltip || item.name,
                locked: item.locked,
                enchants: item.enchants
            });

            // Click listener
            slot.addEventListener('click', (e) => {
                // If right clicked or shift clicked -> toggle lock
                if (e.shiftKey && this.onItemLockToggle) {
                    item.locked = !item.locked;
                    this.onItemLockToggle(item);
                    this._updateView();
                } else if (this.onItemClick) {
                    this.onItemClick(item);
                }
            });

            // Context menu for lock toggle
            slot.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                item.locked = !item.locked;
                if (this.onItemLockToggle) this.onItemLockToggle(item);
                this._updateView();
            });

            this.gridElement.appendChild(slot);
        });
    }

    _injectStyles() {
        if (document.getElementById('inventory-grid-styles')) return;

        const style = document.createElement('style');
        style.id = 'inventory-grid-styles';
        style.textContent = `
            .inventory-system-wrapper {
                display: flex;
                flex-direction: column;
                gap: 12px;
                background-color: #1e1e24;
                padding: 16px;
                border-radius: 10px;
                border: 1px solid #33333f;
                box-shadow: 0 4px 16px rgba(0,0,0,0.4);
                max-width: 100%;
                box-sizing: border-box;
                font-family: sans-serif;
            }
            .inventory-toolbar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 8px;
                padding-bottom: 8px;
                border-bottom: 1px solid #2d2d3a;
            }
            .inventory-filter-group {
                display: flex;
                gap: 4px;
                flex-wrap: wrap;
            }
            .inventory-tab-btn {
                background-color: #2a2a38;
                color: #b0b0c0;
                border: 1px solid #3d3d50;
                padding: 6px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.15s ease;
            }
            .inventory-tab-btn:hover {
                background-color: #38384d;
                color: #fff;
            }
            .inventory-tab-btn.active {
                background-color: #3b82f6;
                color: #fff;
                border-color: #60a5fa;
                font-weight: bold;
            }
            .inventory-sort-group {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .inventory-sort-label {
                color: #94a3b8;
                font-size: 12px;
            }
            .inventory-sort-select {
                background-color: #2a2a38;
                color: #e2e8f0;
                border: 1px solid #3d3d50;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
                cursor: pointer;
            }
            .inventory-grid {
                display: grid;
                grid-template-columns: repeat(var(--grid-cols, 5), 48px);
                gap: 8px;
                padding: 10px;
                background-color: #16161c;
                border: 1px solid #272732;
                border-radius: 8px;
                min-height: 180px;
                justify-content: center;
                align-content: start;
            }
            .inventory-empty-msg {
                grid-column: 1 / -1;
                text-align: center;
                color: #64748b;
                padding: 40px 0;
                font-size: 14px;
            }
            .inventory-pagination {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 12px;
                padding-top: 4px;
            }
            .pagination-btn {
                background-color: #2a2a38;
                color: #e2e8f0;
                border: 1px solid #3d3d50;
                padding: 4px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }
            .pagination-btn:disabled {
                opacity: 0.4;
                cursor: not-allowed;
            }
            .pagination-indicator {
                color: #94a3b8;
                font-size: 12px;
            }
        `;
        document.head.appendChild(style);
    }
}

window.InventoryGrid = InventoryGrid;

