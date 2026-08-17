from pprint import pprint

from modules.data.financial_analysis import analyze_financials


print("=" * 80)
print("ASTOR FINANCIAL ANALYSIS")
print("=" * 80)

result = analyze_financials("ASTOR")

pprint(result)

print()
print("=" * 80)
print("ÖZET")
print("=" * 80)

print("Financial Score       :", result.get("financial_score"))
print("Financial Signal      :", result.get("financial_signal"))
print("Financial Available   :", result.get("financial_available"))
print("Financial Trend Score :", result.get("financial_trend_score"))
print("Financial Trend       :", result.get("financial_trend_signal"))
print("Strong Points         :", result.get("strong_points"))
print("Weak Points           :", result.get("weak_points"))