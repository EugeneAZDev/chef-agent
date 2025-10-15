-- Fix diet_type values to match enum values
-- Migration: 0002_fix_diet_type_values

-- Update existing diet_type values to match DietType enum values
UPDATE recipes SET diet_type = 'low-carb' WHERE diet_type = 'low_carb';
UPDATE recipes SET diet_type = 'high-protein' WHERE diet_type = 'high_protein';
UPDATE recipes SET diet_type = 'gluten-free' WHERE diet_type = 'gluten_free';

-- Add any other necessary corrections
-- Note: This migration ensures consistency between database values and enum values
