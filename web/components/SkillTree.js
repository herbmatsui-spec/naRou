"""
Skill Tree System (Phase 3-C)

Implements a comprehensive skill tree system with:
- Skill nodes with unlock requirements and effects
- Interactive skill tree visualization with hover/click interactions
- Skill selection and activation
- Visual feedback for locked/unlocked/learned skills
- Integration with game state and API
"""

import React, { useState, useEffect } from 'react';
import { skillTreeData } from './skillTreeData.js';
import './SkillTree.css';

const SkillTree = () => {
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [unlockedSkills, setUnlockedSkills] = useState([]);
  const [skillPoints, setSkillPoints] = useState(0);
  
  // Initialize skill tree from data
  const [skillTree, setSkillTree] = useState(skillTreeData);
  
  // Calculate skill points from player state
  useEffect(() => {
    const totalPoints = 0; // Calculate from game state
    setSkillPoints(totalPoints);
  }, []);
  
  // Unlock skill recursively based on prerequisites
  const unlockSkill = (skillId) => {
    const skill = findSkill(skillId);
    if (!skill || skill.unlocked) return false;
    
    // Check all prerequisites are unlocked
    if (skill.prerequisites && skill.prerequisites.some(prereq => !unlockedSkills.includes(prereq))) {
      return false;
    }
    
    // Unlock the skill
    setSkillTree(prev => {
      const newTree = JSON.parse(JSON.stringify(prev));
      const skillToUnlock = findSkillInTree(newTree, skillId);
      if (skillToUnlock) {
        skillToUnlock.unlocked = true;
        // Recursively unlock dependent skills
        if (skillToUnlock.children) {
          skillToUnlock.children.forEach(childId => {
            unlockSkill(childId);
          });
        }
      }
      return newTree;
    });
    
    setUnlockedSkills(prev => [...prev, skillId]);
    return true;
  };
  
  // Find skill in tree by ID
  const findSkillInTree = (tree, skillId) => {
    if (!tree) return null;
    
    if (tree.id === skillId) return tree;
    
    if (tree.children) {
      for (const child of tree.children) {
        const found = findSkillInTree(child, skillId);
        if (found) return found;
      }
    }
    
    return null;
  };
  
  // Find skill from flattened data
  const findSkill = (skillId) => {
    return skillTreeData.find(skill => skill.id === skillId) || 
           skillTreeData.flatMap(s => [s, ...(s.children || [])]).find(skill => skill.id === skillId);
  };
  
  // Handle skill selection
  const handleSkillSelect = (skillId) => {
    const skill bilateral = findSkill(skillId);
    if (!skill bilateral || !skill.unlocked || skill.selected) return;
    
    // Check if we have enough points
    if (skillPoints < skill.cost) {
      return;
    }
    
    // Select the skill
    setSkillTree(prev => {
      const newTree = JSON.parse(JSON.stringify(prev));
      const skillToSelect = findSkillInTree(newTree, skillId);
      if (skillToSelect) {
        skillToSelect.selected = true;
        // Update parent to show it's being used
        const parent = findParent(newTree, skillId);
        if (parent) {
          parent.hasSelectedChild = true;
        }
      }
      return newTree;
    });
    
    setSkillPoints(prev => prev - skill.cost);
    setSelectedSkill(skillId);
  };
  
  // Find parent skill
  const findParent = (tree, skillId) => {
    if (!tree.children) return null;
    
    for (const child of tree.children) {
      if (child.id === skillId) return tree;
      const found = findParent(child, skillId);
      if (found) return found;
    }
    
    return null;
  };
  
  // Get skill tier levels
  const getSkillTier = (skill) => {
    if (!skill) return null;
    
    const tiers = skillTreeData.filter(s => s.tier === skill.tier);
    return tiers.length;
  };
  
  // Render skill node
  const renderSkillNode = (skill, level = 0) => {
    if (!skill) return null;
    
    const isUnlocked = unlockedSkills.includes(skill.id);
    const isSelected = selectedSkill === skill.id;
    const isLocked = !isUnlocked;
    const isMaxLevel = skill.level >= (skill.maxLevel || 1);
    
    const nodeClass = `skill-node ${skill.category} ${isUnlocked ? 'unlocked' : 'locked'} ${isSelected ? 'selected' : ''} ${isMaxLevel ? 'max-level' : ''}`;
    
    return (
      <div 
        className={nodeClass}
        key={skill.id}
        onClick={() => handleSkillSelect(skill.id)}
        style={{ 
          gridColumn: skill.position.col,
          gridRow: skill.position.row,
          marginLeft: `${level * 20}px` 
        }}
      >
        <div className="skill-node-content">
          <div className="skill-icon">
            {skill.icon || '🎯'}
          </div>
          <div className="skill-info">
            <div className="skill-name">{skill.name}</div>
            <div className="skill-description">{skill.description}</div>
            <div className="skill-cost">コスト: {skill.cost}</div>
          </div>
          {isUnlocked && (
            <div className="skill-status">
              {isSelected ? '✓' : '•'}
            </div>
          )}
        </div>
        {isUnlocked && (
          <div className="skill-effects">
            {skill.effects?.map((effect, idx) => (
              <div key={idx} className="effect">
                {effect.type}: {effect.value}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };
  
  // Render skill tree
  const renderSkillTree = () => {
    return (
      <div className="skill-tree-container">
        <div className="skill-tree-header">
          <h2>Skill Tree</h2>
          <div className="skill-points">ポイント: {skillPoints}</div>
        </div>
        
        <div className="skill-tree-grid">
          {skillTree.map(tier => (
            <div key={tier.id} className="skill-tier">
              <div className="tier-header">
                <h3>{tier.name}</h3>
                <div className="tier-level">レベル {tier.level}</div>
              </div>
              <div className="tier-content">
                {tier.children?.map(child => renderSkillNode(child, tier.level))}
              </div>
            </div>
          ))}
        </div>
        
        <div className="skill-details">
          {selectedSkill && (
            <div className="selected-skill-details">
              {(() => {
                const skill = findSkill(selectedSkill);
                return skill ? (
                  <div>
                    <h4>{skill.name}</h4>
                    <p>{skill.description}</p>
                    <div className="skill-stats">
                      <div>カテゴリー: {skill.category}</div>
                      <div>コスト: {skill.cost}</div>
                      <div>効果: {skill.effects?.map(e => `${e.type} ${e.value}`).join(', ')}</div>
                    </div>
                  </div>
                ) : null;
              })()}
            </div>
          )}
        </div>
      </div>
    );
  };
  
  return renderSkillTree();
};

export default SkillTree;