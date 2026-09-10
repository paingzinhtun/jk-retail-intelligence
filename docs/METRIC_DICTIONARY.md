# Metric dictionary

| Metric | Formula | Frequency | Decision | Limitation |
|---|---|---|---|---|
| Revenue | Sum(quantity × selling price − discount) | Daily/5-day | Review demand and cash generation | Excludes unrecorded sales |
| Estimated COGS | Sum(quantity × recorded unit cost) | 5-day | Understand product cost | Not weighted-average accounting |
| Gross profit | Revenue − estimated COGS | 5-day | Allocate shelf space and working capital | Excludes operating expenses |
| Gross margin % | Gross profit ÷ revenue | 5-day | Compare economic contribution | Can mislead on very low volume |
| Units sold | Sum(quantity) | Daily/5-day | Understand product movement | Does not show availability-constrained demand |
| Average basket value | Revenue ÷ distinct transactions | 5-day | Observe basket economics | Requires reliable transaction IDs |
| Estimated stock | Latest count + later purchases − later sales | Daily | Identify stock risk | Fails when transactions are missed |
| Average daily units | Units sold ÷ observed days | Rolling 30-day | Estimate replenishment need | Short history and stockouts bias it downward |
| Reorder point | Avg daily units × lead time + safety stock | Rolling | Decide when to reorder | Simplified; no service-level optimization |
| Suggested reorder quantity | Max(0, target stock − estimated stock) | 5-day | Draft purchase quantity | Requires owner review and cash constraints |
| Data acceptance rate | Accepted rows ÷ received rows | Pipeline run | Judge trustworthiness | Valid rows may still be factually inaccurate |

