/**
 * SkillNode
 * A stateless component representing a single skill or talent in a skill tree.
 */
class SkillNode extends UIComponent {
    /**
     * Render the skill node.
     * @param {Object} props
     * @param {string} props.id - Unique skill ID
     * @param {string} props.name - Display name of the skill
     * @param {string} props.icon - Emoji or icon
     * @param {'locked'|'available'|'learned'} props.state - The current state of the node
     * @param {Object} [props.position] - { x, y } coordinates for placement
     * @returns {HTMLElement}
     */
    render({ id, name, icon = '✨', state = 'locked', position = { x: 0, y: 0 } }) {
        const container = this.createElement('div', {
            id: `skill-node-${id}`,
            className: `skill-node skill-node--${state}`,
            style: `left: ${position.x}px; top: ${position.y}px;`
        }, []);

        const iconElement = this.createElement('div', {
            className: 'skill-node-icon'
        }, [icon]);

        const nameElement = this.createElement('div', {
            className: 'skill-node-name'
        }, [name]);

        container.appendChild(iconElement);
        container.appendChild(nameElement);

        this._injectStyles();

        return container;
    }

    _injectStyles() {
        if (document.getElementById('skill-node-styles')) return;

        const style = document.createElement('style');
        style.id = 'skill-node-styles';
        style.textContent = `
            .skill-node {
                position: absolute;
                width: 80px;
                height: 80px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                cursor: pointer;
                transition: all var(--motion-duration-standard) var(--motion-easing-smooth);
                z-index: 2;
                text-align: center;
                border: 3px solid var(--colors-surface-border);
                background-color: var(--colors-surface-surface-mid);
                box-shadow: 0 4px 8px rgba(0,0,0,0.4);
            }
            .skill-node:hover {
                transform: scale(1.1);
                z-index: 10;
            }
            .skill-node-icon {
                font-size: 24px;
                margin-bottom: 4px;
            }
            .skill-node-name {
                font-size: var(--typography-size-tiny);
                color: var(--colors-content-text-main);
                width: 70px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                font-weight: var(--typography-weight-medium);
            }
            /* States */
            .skill-node--locked {
                filter: grayscale(1);
                opacity: 0.6;
                border-style: dashed;
            }
            .skill-node--available {
                border-color: var(--colors-brand-primary);
                box-shadow: 0 0 15px var(--colors-brand-primary);
                animation: nodePulse var(--motion-duration-slow) infinite alternate ease-in-out;
            }
            .skill-node--learned {
                border-color: var(--colors-brand-accent);
                background-color: var(--colors-surface-surface-high);
                box-shadow: 0 0 10px var(--colors-brand-accent);
            }
            @keyframes nodePulse {
                from { box-shadow: 0 0 5px var(--colors-brand-primary); }
                to { box-shadow: 0 0 20px var(--colors-brand-primary); }
            }
        `;
        document.head.appendChild(style);
    }
}

window.SkillNode = SkillNode;
