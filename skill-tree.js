/**
 * SkillTree
 * A stateless component that manages the layout of SkillNodes and 
 * draws connecting lines between them using SVG.
 */
class SkillTree extends UIComponent {
    /**
     * Render the skill tree.
     * @param {Object} props
     * @param {Array} props.nodes - Array of { id, name, icon, state, position: {x, y} }
     * @param {Array} props.connections - Array of { from: id, to: id }
     * @param {string} [props.id] - Optional element ID
     * @returns {HTMLElement}
     */
    render({ nodes = [], connections = [], id = 'skill-tree' }) {
        const container = this.createElement('div', {
            id: id,
            className: 'skill-tree-container'
        }, []);

        // 1. SVG Layer for connections
        const svg = this.createElement('svg', {
            className: 'skill-tree-svg'
        }, []);
        
        // Determine canvas size based on nodes
        const maxX = Math.max(...nodes.map(n => n.position.x), 0) + 100;
        const maxY = Math.max(...nodes.map(n => n.position.y), 0) + 100;
        svg.setAttribute('width', `${maxX}px`);
        svg.setAttribute('height', `${maxY}px`);

        const nodeComponent = new SkillNode();
        const nodeMap = {};

        // 2. Render Nodes first to populate nodeMap
        nodes.forEach(nodeData => {
            const nodeEl = nodeComponent.render(nodeData);
            container.appendChild(nodeEl);
            nodeMap[nodeData.id] = nodeData.position;
        });

        // 3. Draw Connections
        connections.forEach(conn => {
            const start = nodeMap[conn.from];
            const end = nodeMap[conn.to];

            if (start && end) {
                // Offset to center of the node (Node size is 80px, center is +40px)
                const line = this.createElement('line', {
                    x1: start.x + 40,
                    y1: start.y + 40,
                    x2: end.x + 40,
                    y2: end.y + 40,
                    className: 'skill-tree-connection'
                }, []);
                svg.appendChild(line);
            }
        });

        container.appendChild(svg);
        this._injectStyles();

        return container;
    }

    _injectStyles() {
        if (document.getElementById('skill-tree-styles')) return;

        const style = document.createElement('style');
        style.id = 'skill-tree-styles';
        style.textContent = `
            .skill-tree-container {
                position: relative;
                background-color: var(--colors-surface-surface-low);
                border: 1px solid var(--colors-surface-border);
                border-radius: 12px;
                overflow: auto;
                padding: var(--spacing-8);
                min-width: 600px;
                min-height: 400px;
            }
            .skill-tree-svg {
                position: absolute;
                top: var(--spacing-8);
                left: var(--spacing-8);
                pointer-events: none;
                z-index: 1;
            }
            .skill-tree-connection {
                stroke: var(--colors-surface-surface-high);
                stroke-width: 3;
                stroke-linecap: round;
                transition: stroke var(--motion-duration-standard) var(--motion-easing-smooth);
            }
            /* Highlighting connection when nodes are learned could be added here */
        `;
        document.head.appendChild(style);
    }
}

window.SkillTree = SkillTree;
