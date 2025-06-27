/**
 * Utility functions for camper care filter operations
 */

/**
 * Build query parameters from filter object
 * @param {object} filters - Filter parameters
 * @returns {URLSearchParams} - URL search parameters
 */
export const buildFilterParams = (filters = {}) => {
  const params = new URLSearchParams();
  
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== '' && value != null && value !== undefined) {
      params.append(key, value);
    }
  });
  
  return params;
};

/**
 * Validate filter values
 * @param {object} filters - Filter parameters to validate
 * @returns {object} - Validated filter parameters
 */
export const validateFilters = (filters = {}) => {
  const validated = {};
  
  // Validate bunk_id (should be a number)
  if (filters.bunk_id && !isNaN(filters.bunk_id)) {
    validated.bunk_id = filters.bunk_id.toString();
  }
  
  // Validate boolean fields
  ['unit_head_help', 'camper_care_help'].forEach(key => {
    if (filters[key] === 'true' || filters[key] === true) {
      validated[key] = 'true';
    } else if (filters[key] === 'false' || filters[key] === false) {
      validated[key] = 'false';
    }
  });
  
  // Validate score fields (1-5)
  [
    'social_score_min', 'social_score_max',
    'behavior_score_min', 'behavior_score_max',
    'participation_score_min', 'participation_score_max'
  ].forEach(key => {
    const value = parseInt(filters[key]);
    if (!isNaN(value) && value >= 1 && value <= 5) {
      validated[key] = value.toString();
    }
  });
  
  return validated;
};

/**
 * Get filter summary for display
 * @param {object} filters - Current filter values
 * @returns {object} - Summary with count and description
 */
export const getFilterSummary = (filters = {}) => {
  const activeFilters = Object.entries(filters).filter(
    ([_, value]) => value !== '' && value != null
  );
  
  const count = activeFilters.length;
  
  if (count === 0) {
    return { count: 0, description: 'No filters applied' };
  }
  
  const descriptions = activeFilters.map(([key, value]) => {
    switch (key) {
      case 'bunk_id':
        return `Bunk: ${value}`;
      case 'unit_head_help':
        return value === 'true' ? 'Unit Head Help' : 'No Unit Head Help';
      case 'camper_care_help':
        return value === 'true' ? 'Camper Care Help' : 'No Camper Care Help';
      case 'social_score_min':
        return `Social ≥ ${value}`;
      case 'social_score_max':
        return `Social ≤ ${value}`;
      case 'behavior_score_min':
        return `Behavior ≥ ${value}`;
      case 'behavior_score_max':
        return `Behavior ≤ ${value}`;
      case 'participation_score_min':
        return `Participation ≥ ${value}`;
      case 'participation_score_max':
        return `Participation ≤ ${value}`;
      default:
        return `${key}: ${value}`;
    }
  });
  
  return {
    count,
    description: descriptions.join(', ')
  };
};

/**
 * Predefined filter presets
 */
export const FILTER_PRESETS = {
  needsAttention: {
    label: "Needs Attention",
    filters: { camper_care_help: 'true', social_score_max: '2' },
    color: "destructive",
    description: "Campers requesting camper care help with low social scores"
  },
  helpRequested: {
    label: "Help Requested", 
    filters: { unit_head_help: 'true' },
    color: "secondary",
    description: "Campers with unit head help requests"
  },
  highAchievers: {
    label: "High Achievers",
    filters: { social_score_min: '4', behavior_score_min: '4' },
    color: "default",
    description: "Campers with high social and behavior scores"
  },
  lowParticipation: {
    label: "Low Participation",
    filters: { participation_score_max: '2' },
    color: "outline",
    description: "Campers with low participation scores"
  },
  criticalIssues: {
    label: "Critical Issues",
    filters: { 
      camper_care_help: 'true', 
      behavior_score_max: '2',
      social_score_max: '2'
    },
    color: "destructive",
    description: "Campers needing immediate attention"
  }
};

/**
 * Calculate statistics from camper data
 * @param {array} data - Camper data array
 * @returns {object} - Calculated statistics
 */
export const calculateCamperStats = (data = []) => {
  let totalCampers = 0;
  let totalBunks = 0;
  let helpRequests = 0;
  let scores = { social: [], behavior: [], participation: [] };

  data.forEach(unit => {
    unit.bunks?.forEach(bunk => {
      if (bunk.campers?.length > 0) totalBunks++;
      
      bunk.campers?.forEach(camper => {
        totalCampers++;
        
        if (camper.bunk_log) {
          const log = camper.bunk_log;
          if (log.request_unit_head_help || log.request_camper_care_help) {
            helpRequests++;
          }
          
          if (log.social_score) scores.social.push(log.social_score);
          if (log.behavior_score) scores.behavior.push(log.behavior_score);
          if (log.participation_score) scores.participation.push(log.participation_score);
        }
      });
    });
  });

  const calculateAverage = (arr) => 
    arr.length > 0 ? (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(1) : '—';

  return {
    totalCampers,
    totalBunks,
    helpRequests,
    averageScores: {
      social: calculateAverage(scores.social),
      behavior: calculateAverage(scores.behavior),
      participation: calculateAverage(scores.participation)
    },
    scoreDistribution: {
      social: getScoreDistribution(scores.social),
      behavior: getScoreDistribution(scores.behavior),
      participation: getScoreDistribution(scores.participation)
    }
  };
};

/**
 * Get score distribution (count by score value)
 * @param {array} scores - Array of score values
 * @returns {object} - Distribution by score
 */
const getScoreDistribution = (scores) => {
  const distribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
  scores.forEach(score => {
    if (distribution[score] !== undefined) {
      distribution[score]++;
    }
  });
  return distribution;
};

/**
 * Format filter value for display
 * @param {string} key - Filter key
 * @param {*} value - Filter value
 * @returns {string} - Formatted display string
 */
export const formatFilterValue = (key, value) => {
  if (key.includes('help')) {
    return value === 'true' ? 'Yes' : 'No';
  }
  
  if (key.includes('score')) {
    const scoreLabels = {
      1: 'Poor',
      2: 'Below Average', 
      3: 'Average',
      4: 'Good',
      5: 'Excellent'
    };
    return `${value} (${scoreLabels[value] || 'Unknown'})`;
  }
  
  return value;
};

/**
 * Debounce function for search inputs
 * @param {function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {function} - Debounced function
 */
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

export default {
  buildFilterParams,
  validateFilters,
  getFilterSummary,
  FILTER_PRESETS,
  calculateCamperStats,
  formatFilterValue,
  debounce
};
