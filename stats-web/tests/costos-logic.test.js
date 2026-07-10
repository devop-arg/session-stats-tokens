'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  getComparableSubscriptionCost,
  getCostNeighbors,
  calculateBreakEven,
} = require('../static/costos-logic.js');

test('prioriza el costo manual de suscripción', () => {
  const result = getComparableSubscriptionCost({
    model: 'gpt-manual',
    plan: 'Codex ($20/mes)',
    cost_api: 0.4,
    cost_sub: 0.03,
  });

  assert.deepEqual(result, {
    value: 0.03,
    pending: false,
    source: 'manual',
  });
});

test('usa costo API dividido 20 para Codex sin precio manual', () => {
  const result = getComparableSubscriptionCost({
    model: 'gpt-pending',
    plan: 'Codex ($20/mes)',
    cost_api: 0.4,
    cost_sub: 0,
  });

  assert.deepEqual(result, {
    value: 0.02,
    pending: true,
    source: 'fallback',
  });
});

test('no inventa fallback para modelos sin plan Codex', () => {
  assert.equal(getComparableSubscriptionCost({
    model: 'modelo-sin-plan',
    plan: null,
    cost_api: 0.4,
    cost_sub: null,
  }), null);
});

test('devuelve cinco vecinos estrictamente más baratos y cinco más caros', () => {
  const models = [];
  for (let i = 1; i <= 13; i += 1) {
    models.push({
      model: `modelo-${i}`,
      plan: 'Codex ($20/mes)',
      cost_api: i,
      cost_sub: i,
    });
  }

  const result = getCostNeighbors(models, 'modelo-7', 5);

  assert.equal(result.selected.model, 'modelo-7');
  assert.deepEqual(result.cheaper.map((item) => item.model), [
    'modelo-2', 'modelo-3', 'modelo-4', 'modelo-5', 'modelo-6',
  ]);
  assert.deepEqual(result.pricier.map((item) => item.model), [
    'modelo-8', 'modelo-9', 'modelo-10', 'modelo-11', 'modelo-12',
  ]);
});

test('usa fallback pendiente dentro del orden comparativo', () => {
  const models = [
    { model: 'barato', plan: 'Codex ($20/mes)', cost_api: 0.2, cost_sub: 0.005 },
    { model: 'elegido', plan: 'Codex ($20/mes)', cost_api: 0.4, cost_sub: 0 },
    { model: 'caro', plan: 'Codex ($20/mes)', cost_api: 0.5, cost_sub: 0.04 },
  ];

  const result = getCostNeighbors(models, 'elegido', 5);

  assert.equal(result.selected.comparisonCost, 0.02);
  assert.equal(result.selected.pricePending, true);
  assert.deepEqual(result.cheaper.map((item) => item.model), ['barato']);
  assert.deepEqual(result.pricier.map((item) => item.model), ['caro']);
});

test('devuelve todos los vecinos disponibles cuando hay menos de cinco', () => {
  const models = [
    { model: 'a', plan: 'Codex ($20/mes)', cost_api: 0.1, cost_sub: 0.01 },
    { model: 'b', plan: 'Codex ($20/mes)', cost_api: 0.2, cost_sub: 0.02 },
  ];

  const result = getCostNeighbors(models, 'a', 5);

  assert.deepEqual(result.cheaper, []);
  assert.deepEqual(result.pricier.map((item) => item.model), ['b']);
});

test('calcula el punto de equilibrio semanal y su porcentaje de ventana', () => {
  const result = calculateBreakEven({
    monthlyPlanCost: 20,
    apiCostPerMillion: 0.5,
    fullWindowTokensM: 100,
  });

  assert.deepEqual(result, {
    weeklyPlanCost: 5,
    tokensMillions: 10,
    windowPercent: 10,
  });
});

test('devuelve null cuando no se puede calcular el punto de equilibrio', () => {
  assert.equal(calculateBreakEven({
    monthlyPlanCost: 20,
    apiCostPerMillion: 0,
    fullWindowTokensM: 100,
  }), null);

  assert.equal(calculateBreakEven({
    monthlyPlanCost: 0,
    apiCostPerMillion: 0.5,
    fullWindowTokensM: 100,
  }), null);
});
