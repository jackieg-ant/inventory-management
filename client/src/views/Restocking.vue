<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.subtitle') }}</p>
    </div>

    <!-- Budget Card -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budget') }}</h3>
      </div>
      <div class="budget-body">
        <div class="budget-slider-row">
          <input
            type="range"
            class="budget-slider"
            min="0"
            max="100000"
            step="1000"
            v-model.number="budget"
          />
          <span class="budget-amount">{{ formatCurrency(budget) }}</span>
        </div>
        <div class="budget-stats">
          <div class="budget-stat">
            <span class="budget-stat-label">{{ t('restocking.selectedTotal') }}:</span>
            <span class="budget-stat-value">{{ formatCurrency(selectedTotal) }}</span>
          </div>
          <div class="budget-stat">
            <span class="budget-stat-label">{{ t('restocking.remaining') }}:</span>
            <span class="budget-stat-value" :class="{ 'over-budget': remaining < 0 }">
              {{ formatCurrency(remaining) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Recommendations Card -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
      </div>

      <div v-if="loadingRecs" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="recsError" class="error">{{ recsError }}</div>
      <div v-else>
        <div class="table-container">
          <table class="recs-table">
            <thead>
              <tr>
                <th class="col-check"></th>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th>{{ t('restocking.table.stock') }}</th>
                <th>{{ t('restocking.table.forecast') }}</th>
                <th>{{ t('restocking.table.shortage') }}</th>
                <th>{{ t('restocking.table.qty') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="rec in localRecs"
                :key="rec.sku"
                :class="{ 'row-selected': rec.checked }"
              >
                <td class="col-check">
                  <input type="checkbox" v-model="rec.checked" />
                </td>
                <td><strong>{{ rec.sku }}</strong></td>
                <td>{{ rec.item_name }}</td>
                <td>{{ rec.current_stock }}</td>
                <td>{{ rec.forecasted_demand }}</td>
                <td>
                  <span :class="rec.shortage > 0 ? 'shortage-positive' : 'shortage-zero'">
                    {{ rec.shortage }}
                  </span>
                </td>
                <td class="col-qty">
                  <input
                    type="number"
                    class="qty-input"
                    v-model.number="rec.qty"
                    min="0"
                    :disabled="!rec.checked"
                  />
                </td>
                <td>{{ formatCurrency(rec.unit_cost) }}</td>
                <td><strong>{{ formatCurrency(rec.checked ? rec.qty * rec.unit_cost : 0) }}</strong></td>
                <td>{{ rec.lead_time_days }} {{ t('restocking.orders.days') }}</td>
                <td>
                  <span :class="['badge', rec.trend]">{{ rec.trend }}</span>
                </td>
              </tr>
            </tbody>
            <tfoot v-if="localRecs.length > 0">
              <tr class="summary-row">
                <td colspan="6" class="summary-label">
                  {{ checkedCount }} item{{ checkedCount !== 1 ? 's' : '' }} selected
                </td>
                <td colspan="3" class="summary-total">
                  {{ formatCurrency(selectedTotal) }}
                </td>
                <td colspan="2"></td>
              </tr>
            </tfoot>
          </table>
        </div>

        <div class="order-action-row">
          <div class="order-messages">
            <span v-if="successMsg" class="success-msg">{{ successMsg }}</span>
            <span v-if="selectedTotal > budget && selectedTotal > 0" class="warn-msg">
              {{ t('restocking.overBudget') }}
            </span>
          </div>
          <button
            class="btn-place-order"
            :disabled="placing || selectedTotal === 0 || selectedTotal > budget"
            @click="placeOrder"
          >
            {{ placing ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Submitted Orders Card -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.submittedOrders') }}</h3>
      </div>

      <div v-if="loadingOrders" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="ordersError" class="error">{{ ordersError }}</div>
      <div v-else-if="submittedOrders.length === 0" class="empty-state">
        {{ t('restocking.noOrders') }}
      </div>
      <div v-else class="table-container">
        <table class="orders-table">
          <thead>
            <tr>
              <th>{{ t('restocking.orders.id') }}</th>
              <th>{{ t('restocking.orders.submitted') }}</th>
              <th>{{ t('restocking.orders.items') }}</th>
              <th>{{ t('restocking.orders.total') }}</th>
              <th>{{ t('restocking.orders.leadTime') }}</th>
              <th>{{ t('restocking.orders.expected') }}</th>
              <th>{{ t('restocking.orders.status') }}</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="order in submittedOrders" :key="order.id">
              <tr
                class="order-row"
                :class="{ 'order-expanded': expandedOrderId === order.id }"
                @click="toggleExpand(order.id)"
              >
                <td><strong>{{ order.id }}</strong></td>
                <td>{{ formatDate(order.submitted_at) }}</td>
                <td>{{ order.items.length }}</td>
                <td><strong>{{ formatCurrency(order.total_cost) }}</strong></td>
                <td>{{ order.max_lead_time_days }} {{ t('restocking.orders.days') }}</td>
                <td>{{ formatDate(order.expected_delivery) }}</td>
                <td>
                  <span class="badge info">{{ order.status }}</span>
                </td>
              </tr>
              <tr v-if="expandedOrderId === order.id" :key="order.id + '-detail'" class="detail-row">
                <td colspan="7" class="detail-cell">
                  <table class="nested-table">
                    <thead>
                      <tr>
                        <th>{{ t('restocking.table.sku') }}</th>
                        <th>{{ t('restocking.table.name') }}</th>
                        <th>{{ t('restocking.table.qty') }}</th>
                        <th>{{ t('restocking.table.unitCost') }}</th>
                        <th>{{ t('restocking.table.lineCost') }}</th>
                        <th>{{ t('restocking.table.leadTime') }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="item in order.items" :key="item.sku">
                        <td><strong>{{ item.sku }}</strong></td>
                        <td>{{ item.item_name }}</td>
                        <td>{{ item.quantity }}</td>
                        <td>{{ formatCurrency(item.unit_cost) }}</td>
                        <td>{{ formatCurrency(item.line_cost) }}</td>
                        <td>{{ item.lead_time_days }} {{ t('restocking.orders.days') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t } = useI18n()

    // Budget
    const budget = ref(25000)

    // Recommendations state
    const loadingRecs = ref(false)
    const recsError = ref(null)
    const localRecs = ref([])

    // Order submission state
    const placing = ref(false)
    const successMsg = ref('')

    // Submitted orders state
    const loadingOrders = ref(false)
    const ordersError = ref(null)
    const submittedOrders = ref([])
    const expandedOrderId = ref(null)

    // Debounce timer
    let debounceTimer = null

    const fetchRecommendations = async () => {
      loadingRecs.value = true
      recsError.value = null
      try {
        const data = await api.getRestockRecommendations(budget.value)
        localRecs.value = data.map(rec => ({
          ...rec,
          checked: rec.selected,
          qty: rec.recommended_qty
        }))
      } catch (err) {
        recsError.value = 'Failed to load recommendations: ' + err.message
        console.error(err)
      } finally {
        loadingRecs.value = false
      }
    }

    const fetchOrders = async () => {
      loadingOrders.value = true
      ordersError.value = null
      try {
        submittedOrders.value = await api.getRestockOrders()
      } catch (err) {
        ordersError.value = 'Failed to load orders: ' + err.message
        console.error(err)
      } finally {
        loadingOrders.value = false
      }
    }

    // Computed
    const selectedTotal = computed(() => {
      return localRecs.value
        .filter(r => r.checked)
        .reduce((sum, r) => sum + r.qty * r.unit_cost, 0)
    })

    const remaining = computed(() => budget.value - selectedTotal.value)

    const checkedCount = computed(() => localRecs.value.filter(r => r.checked).length)

    // Watch budget with 250ms debounce
    watch(budget, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        fetchRecommendations()
      }, 250)
    })

    const placeOrder = async () => {
      if (placing.value || selectedTotal.value === 0 || selectedTotal.value > budget.value) return

      placing.value = true
      successMsg.value = ''
      try {
        const items = localRecs.value
          .filter(r => r.checked && r.qty > 0)
          .map(r => ({
            sku: r.sku,
            item_name: r.item_name,
            quantity: r.qty,
            unit_cost: r.unit_cost,
            line_cost: Math.round(r.qty * r.unit_cost * 100) / 100,
            lead_time_days: r.lead_time_days,
          }))

        const result = await api.createRestockOrder({
          budget: budget.value,
          items
        })

        successMsg.value = t('restocking.orderPlaced', { id: result.id })
        await Promise.all([fetchOrders(), fetchRecommendations()])
      } catch (err) {
        recsError.value = 'Failed to place order: ' + err.message
        console.error(err)
      } finally {
        placing.value = false
      }
    }

    const toggleExpand = (orderId) => {
      expandedOrderId.value = expandedOrderId.value === orderId ? null : orderId
    }

    const formatCurrency = (value) => {
      if (typeof value !== 'number') return '$0'
      return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
    }

    const formatDate = (dateString) => {
      if (!dateString) return ''
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
    }

    onMounted(() => {
      fetchRecommendations()
      fetchOrders()
    })

    return {
      t,
      budget,
      loadingRecs,
      recsError,
      localRecs,
      placing,
      successMsg,
      loadingOrders,
      ordersError,
      submittedOrders,
      expandedOrderId,
      selectedTotal,
      remaining,
      checkedCount,
      placeOrder,
      toggleExpand,
      formatCurrency,
      formatDate
    }
  }
}
</script>

<style scoped>
/* Budget card */
.budget-body {
  padding-top: 0.5rem;
}

.budget-slider-row {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  margin-bottom: 1rem;
}

.budget-slider {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #e2e8f0;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}

.budget-amount {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  min-width: 110px;
  text-align: right;
}

.budget-stats {
  display: flex;
  gap: 2.5rem;
}

.budget-stat {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.budget-stat-label {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
}

.budget-stat-value {
  font-size: 0.938rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-stat-value.over-budget {
  color: #dc2626;
}

/* Recommendations table */
.recs-table {
  width: 100%;
  border-collapse: collapse;
}

.col-check {
  width: 40px;
  text-align: center;
}

.col-qty {
  width: 90px;
}

.qty-input {
  width: 70px;
  padding: 0.25rem 0.375rem;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 0.875rem;
  color: #0f172a;
  background: white;
}

.qty-input:disabled {
  background: #f8fafc;
  color: #94a3b8;
  cursor: not-allowed;
}

.qty-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.row-selected {
  background-color: #f0fdf4;
}

.row-selected:hover {
  background-color: #dcfce7 !important;
}

.shortage-positive {
  color: #dc2626;
  font-weight: 600;
}

.shortage-zero {
  color: #64748b;
}

/* Summary footer row */
.summary-row td {
  border-top: 2px solid #e2e8f0;
  background: #f8fafc;
  font-size: 0.875rem;
  padding: 0.625rem 0.75rem;
}

.summary-label {
  color: #64748b;
  font-weight: 500;
}

.summary-total {
  color: #0f172a;
  font-weight: 700;
  font-size: 0.938rem;
}

/* Order action row */
.order-action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.order-messages {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.success-msg {
  font-size: 0.875rem;
  color: #059669;
  font-weight: 500;
}

.warn-msg {
  font-size: 0.875rem;
  color: #dc2626;
  font-weight: 500;
}

.btn-place-order {
  padding: 0.625rem 1.5rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn-place-order:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-place-order:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

/* Submitted orders table */
.order-row {
  cursor: pointer;
}

.order-row:hover {
  background: #f8fafc;
}

.order-expanded {
  background: #eff6ff;
}

.order-expanded:hover {
  background: #dbeafe !important;
}

.detail-row {
  background: #f8fafc;
}

.detail-cell {
  padding: 1rem 1.5rem !important;
  border-bottom: 1px solid #e2e8f0;
}

/* Nested table */
.nested-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

.nested-table thead {
  background: #f1f5f9;
}

.nested-table th {
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  text-align: left;
}

.nested-table td {
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: #334155;
  border-top: 1px solid #f1f5f9;
}

/* Empty state */
.empty-state {
  padding: 2.5rem;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
}
</style>
