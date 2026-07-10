(function (root, factory) {
  'use strict';

  var api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.CostosLogic = api;
  }
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function positiveNumber(value) {
    var number = Number(value);
    return Number.isFinite(number) && number > 0 ? number : null;
  }

  function getComparableSubscriptionCost(model) {
    if (!model) return null;

    var manualCost = positiveNumber(model.cost_sub);
    if (manualCost !== null) {
      return {
        value: manualCost,
        pending: false,
        source: 'manual'
      };
    }

    var plan = String(model.plan || '').toLowerCase();
    var apiCost = positiveNumber(model.cost_api);
    if (plan.indexOf('codex') !== -1 && apiCost !== null) {
      return {
        value: apiCost / 20,
        pending: true,
        source: 'fallback'
      };
    }

    return null;
  }

  function decorateComparableModel(model) {
    var comparable = getComparableSubscriptionCost(model);
    if (!comparable) return null;

    return Object.assign({}, model, {
      comparisonCost: comparable.value,
      pricePending: comparable.pending,
      comparisonSource: comparable.source
    });
  }

  function getCostNeighbors(models, selectedModel, count) {
    var limit = Number.isInteger(count) && count > 0 ? count : 5;
    var comparableModels = (models || [])
      .map(decorateComparableModel)
      .filter(Boolean)
      .sort(function (a, b) {
        if (a.comparisonCost !== b.comparisonCost) {
          return a.comparisonCost - b.comparisonCost;
        }
        return String(a.model).localeCompare(String(b.model));
      });

    var selected = comparableModels.find(function (item) {
      return item.model === selectedModel;
    }) || null;

    if (!selected) {
      return { cheaper: [], selected: null, pricier: [] };
    }

    var cheaper = comparableModels.filter(function (item) {
      return item.comparisonCost < selected.comparisonCost;
    }).slice(-limit);

    var pricier = comparableModels.filter(function (item) {
      return item.comparisonCost > selected.comparisonCost;
    }).slice(0, limit);

    return {
      cheaper: cheaper,
      selected: selected,
      pricier: pricier
    };
  }

  function calculateBreakEven(options) {
    options = options || {};
    var monthlyPlanCost = positiveNumber(options.monthlyPlanCost);
    var apiCostPerMillion = positiveNumber(options.apiCostPerMillion);
    if (monthlyPlanCost === null || apiCostPerMillion === null) return null;

    var weeklyPlanCost = monthlyPlanCost / 4;
    var tokensMillions = weeklyPlanCost / apiCostPerMillion;
    var fullWindowTokensM = positiveNumber(options.fullWindowTokensM);

    return {
      weeklyPlanCost: weeklyPlanCost,
      tokensMillions: tokensMillions,
      windowPercent: fullWindowTokensM === null ? null : (tokensMillions / fullWindowTokensM) * 100
    };
  }

  return {
    getComparableSubscriptionCost: getComparableSubscriptionCost,
    getCostNeighbors: getCostNeighbors,
    calculateBreakEven: calculateBreakEven
  };
}));
