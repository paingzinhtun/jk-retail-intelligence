import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.env.JK_PROJECT_ROOT ? path.resolve(process.env.JK_PROJECT_ROOT) : path.resolve(".");
const rawDir = path.join(root, "data", "raw");
const processedDir = path.join(root, "data", "processed");
const outputDir = path.join(root, "outputs");
const font = "Arial";
const navy = "#17365D";
const blue = "#2F75B5";
const lightBlue = "#D9EAF7";
const amber = "#FFF2CC";
const red = "#FCE4D6";
const green = "#E2F0D9";
const gray = "#E7E6E6";

function parseCsv(text) {
  const rows = [];
  let row = [], value = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i], next = text[i + 1];
    if (c === '"' && quoted && next === '"') { value += '"'; i++; }
    else if (c === '"') quoted = !quoted;
    else if (c === ',' && !quoted) { row.push(value); value = ""; }
    else if ((c === '\n' || c === '\r') && !quoted) {
      if (c === '\r' && next === '\n') i++;
      row.push(value); value = "";
      if (row.some(x => x !== "")) rows.push(row);
      row = [];
    } else value += c;
  }
  if (value || row.length) { row.push(value); rows.push(row); }
  return rows;
}

async function csv(name, source = processedDir) {
  return parseCsv(await fs.readFile(path.join(source, name), "utf8"));
}

function numericRows(rows, numericHeaders, dateHeaders = []) {
  const headers = rows[0];
  return [headers, ...rows.slice(1).map(r => r.map((v, i) => {
    if (numericHeaders.includes(headers[i])) return v === "" ? null : Number(v);
    if (dateHeaders.includes(headers[i])) return v ? new Date(v) : null;
    if (v === "True") return true;
    if (v === "False") return false;
    return v;
  }))];
}

function applyBase(sheet, usedRange) {
  sheet.showGridLines = false;
  usedRange.format.font = { name: font, size: 10, color: "#222222" };
  usedRange.format.verticalAlignment = "center";
}

function styleHeader(range) {
  range.format = {
    fill: navy,
    font: { name: font, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "inside", style: "thin", color: "#FFFFFF" }
  };
  range.format.rowHeight = 30;
}

function addTitle(sheet, title, subtitle) {
  sheet.getRange("A2:H2").merge();
  sheet.getRange("A2").values = [[title]];
  sheet.getRange("A2").format.font = { name: font, size: 16, bold: true, color: navy };
  sheet.getRange("A3:H3").merge();
  sheet.getRange("A3").values = [[subtitle]];
  sheet.getRange("A3").format.font = { name: font, size: 10, italic: true, color: "#666666" };
  sheet.getRange("A4:H4").format.borders = { bottom: { style: "thin", color: blue } };
}

const products = numericRows(await csv("products.csv", rawDir), ["default_purchase_price","default_selling_price","reorder_level"]);
const sales = numericRows(await csv("sales_clean.csv"), ["quantity","unit_selling_price","unit_cost","discount_mmk","revenue_mmk","estimated_cogs_mmk","gross_profit_mmk"], ["sale_datetime"]);
const daily = numericRows(await csv("daily_performance.csv"), ["revenue_mmk","gross_profit_mmk","transactions"], ["sale_date"]);
const reorder = numericRows(await csv("inventory_recommendations.csv"), ["default_purchase_price","default_selling_price","reorder_level","counted_quantity","sold_after_count","bought_after_count","estimated_stock","avg_daily_units","lead_time_days","safety_stock","calculated_reorder_point","effective_reorder_point","target_stock","suggested_reorder_qty"], ["count_date"]);
const quality = numericRows(await csv("data_quality_summary.csv"), ["received_rows","accepted_rows","rejected_rows","acceptance_rate"]);
const performance = numericRows(await csv("product_performance_30d.csv"), ["default_purchase_price","default_selling_price","reorder_level","units_sold","revenue_mmk","estimated_cogs_mmk","gross_profit_mmk","transactions","gross_margin_pct","avg_daily_units"]);
const summary = JSON.parse(await fs.readFile(path.join(processedDir, "management_summary.json"), "utf8"));

const wb = Workbook.create();
const dashboard = wb.worksheets.add("Dashboard");
const reorderSheet = wb.worksheets.add("Reorder");
const performanceSheet = wb.worksheets.add("Product Performance");
const dailySheet = wb.worksheets.add("Daily Trend");
const qualitySheet = wb.worksheets.add("Data Quality");
const salesSheet = wb.worksheets.add("Sales Clean");
const productsSheet = wb.worksheets.add("Products");
const readme = wb.worksheets.add("ReadMe");

// Source sheets first so dashboard formulas can reference them.
productsSheet.getRange("A1").write(products);
salesSheet.getRange("A1").write(sales);
dailySheet.getRange("A1").write(daily);
qualitySheet.getRange("A1").write(quality);
performanceSheet.getRange("A1").write(performance);
reorderSheet.getRange("A1").write(reorder);

for (const [sheet, rows] of [[productsSheet,products],[salesSheet,sales],[dailySheet,daily],[qualitySheet,quality],[performanceSheet,performance],[reorderSheet,reorder]]) {
  applyBase(sheet, sheet.getRangeByIndexes(0,0,rows.length,rows[0].length));
  styleHeader(sheet.getRangeByIndexes(0,0,1,rows[0].length));
  sheet.freezePanes.freezeRows(1);
  sheet.getUsedRange().format.autofitColumns();
  sheet.getUsedRange().format.autofitRows();
}

productsSheet.getRange(`E2:F${products.length}`).format.numberFormat = "#,##0 \"MMK\"";
salesSheet.getRange(`C2:C${sales.length}`).format.numberFormat = "yyyy-mm-dd hh:mm";
salesSheet.getRange(`E2:K${sales.length}`).format.numberFormat = "#,##0";
dailySheet.getRange(`A2:A${daily.length}`).format.numberFormat = "yyyy-mm-dd";
dailySheet.getRange(`B2:C${daily.length}`).format.numberFormat = "#,##0 \"MMK\"";
qualitySheet.getRange(`E2:E${quality.length}`).format.numberFormat = "0.0%";
performanceSheet.getRange(`E2:F${performance.length}`).format.numberFormat = "#,##0 \"MMK\"";
performanceSheet.getRange(`K2:M${performance.length}`).format.numberFormat = "#,##0";
performanceSheet.getRange(`N2:N${performance.length}`).format.numberFormat = "0.0%";
reorderSheet.getRange(`E2:F${reorder.length}`).format.numberFormat = "#,##0 \"MMK\"";

const statusIndex = reorder[0].indexOf("stock_status");
const statusCol = String.fromCharCode(65 + statusIndex);
reorderSheet.getRange(`${statusCol}2:${statusCol}${reorder.length}`).conditionalFormats.add("containsText", { text: "REORDER", format: { fill: red, font: { bold: true, color: "#9C0006" } } });
reorderSheet.getRange(`${statusCol}2:${statusCol}${reorder.length}`).conditionalFormats.add("containsText", { text: "OK", format: { fill: green, font: { color: "#375623" } } });

applyBase(dashboard, dashboard.getRange("A1:N40"));
addTitle(dashboard, "JK Retail Intelligence", `Synthetic Myanmar retail demonstration | As of ${summary.as_of_date}`);
dashboard.getRange("A6:B6").values = [["Metric","Value"]];
dashboard.getRange("A7:A12").values = [["Five-day revenue"],["Five-day gross profit"],["Gross margin"],["Transactions"],["Average basket value"],["Products requiring reorder"]];
dashboard.getRange("B7").formulas = [[`=SUM('Daily Trend'!B${daily.length-4}:B${daily.length})`]];
dashboard.getRange("B8").formulas = [[`=SUM('Daily Trend'!C${daily.length-4}:C${daily.length})`]];
dashboard.getRange("B9").formulas = [["=IFERROR(B8/B7,0)"]];
dashboard.getRange("B10:B12").values = [[summary.last_5_day_transactions],[summary.average_basket_mmk],[summary.products_requiring_reorder]];
styleHeader(dashboard.getRange("A6:B6"));
dashboard.getRange("A7:A12").format.fill = lightBlue;
dashboard.getRange("A7:A12").format.font = { name: font, size: 10, bold: true, color: navy };
dashboard.getRange("B7:B8").format.numberFormat = "#,##0 \"MMK\"";
dashboard.getRange("B9").format.numberFormat = "0.0%";
dashboard.getRange("B10:B12").format.numberFormat = "#,##0";
dashboard.getRange("A6:B12").format.borders = { preset: "outside", style: "thin", color: "#A6A6A6" };

dashboard.getRange("A15:D15").values = [["Priority","Product","Estimated stock","Suggested order"]];
styleHeader(dashboard.getRange("A15:D15"));
const reorders = reorder.slice(1).filter(r => r[statusIndex] === "REORDER").sort((a,b) => b[reorder[0].indexOf("suggested_reorder_qty")] - a[reorder[0].indexOf("suggested_reorder_qty")]).slice(0,10);
const pName = reorder[0].indexOf("product_name"), est = reorder[0].indexOf("estimated_stock"), qty = reorder[0].indexOf("suggested_reorder_qty");
dashboard.getRange("A16").write(reorders.map((r,i) => [i+1,r[pName],r[est],r[qty]]));
dashboard.getRange(`A16:D${15+reorders.length}`).format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
dashboard.getRange(`D16:D${15+reorders.length}`).format.fill = amber;

dashboard.getRange("O1:Q1").values = [["Date","Revenue","Gross profit"]];
const recentDaily = daily.slice(-30).map(r => [r[0].toISOString().slice(0,10), r[1], r[2]]);
dashboard.getRange("O2").write(recentDaily);
const lineChart = dashboard.charts.add("line", dashboard.getRange("O1:Q31"));
lineChart.title = "Daily sales and gross profit (MMK)";
lineChart.hasLegend = true;
lineChart.setPosition("E6", "N19");
const barChart = dashboard.charts.add("bar", performanceSheet.getRange(`B1:B11`));
// Rebuild with a compact helper so category labels and values are explicit.
dashboard.getRange("J24:K24").values = [["Product","Gross profit"]];
const top = performance.slice(1).sort((a,b)=>b[performance[0].indexOf("gross_profit_mmk")]-a[performance[0].indexOf("gross_profit_mmk")]).slice(0,10);
dashboard.getRange("J25").write(top.map(r=>[r[performance[0].indexOf("product_name")],r[performance[0].indexOf("gross_profit_mmk")]]));
barChart.setData(dashboard.getRange("J24:K34"));
barChart.title = "Top products by 30-day gross profit";
barChart.hasLegend = false;
barChart.setPosition("E21", "N37");
dashboard.getRange("J24:K34").format.font.color = "#FFFFFF";
dashboard.getRange("J24:K34").format.fill = "#FFFFFF";
dashboard.getRange("O1:Q31").format.font.color = "#FFFFFF";
dashboard.getRange("O1:Q31").format.fill = "#FFFFFF";
dashboard.getRange("A1:N40").format.columnWidth = 14;
dashboard.getRange("A:A").format.columnWidth = 34;
dashboard.getRange("B:B").format.columnWidth = 28;
dashboard.getRange("C:D").format.columnWidth = 18;

readme.showGridLines = false;
addTitle(readme, "How to use this workbook", "Generated for the JK Retail Intelligence MVP");
readme.getRange("A6:B13").values = [
  ["Item","Guidance"],
  ["Data status","All transactions are realistic synthetic data, not verified customer records."],
  ["Dashboard","Review five-day performance and priority reorder items."],
  ["Reorder","Owner must confirm supplier availability, cash, and shelf reality before ordering."],
  ["Product Performance","Compare 30-day product revenue, profit, margin, and movement."],
  ["Daily Trend","Review changes over time. A trend does not establish a cause."],
  ["Data Quality","Inspect acceptance rates and rejected records from the Python pipeline."],
  ["Refresh","Replace source CSV files and rerun the generator pipeline and workbook builder."]
];
styleHeader(readme.getRange("A6:B6"));
readme.getRange("A7:A13").format.fill = lightBlue;
readme.getRange("A7:A13").format.font = { name: font, size: 10, bold: true, color: navy };
readme.getRange("A6:B13").format.borders = { preset: "outside", style: "thin", color: gray };
readme.getRange("A:A").format.columnWidth = 24;
readme.getRange("B:B").format.columnWidth = 78;
readme.getRange("B7:B13").format.wrapText = true;
readme.getRange("B7:B13").format.rowHeight = 32;

dashboard.tabColor = navy;
reorderSheet.tabColor = blue;
readme.tabColor = "#7F8C8D";

wb.recalculate();
const dashboardCheck = await wb.inspect({kind:"table",range:"Dashboard!A6:D25",include:"values,formulas",tableMaxRows:25,tableMaxCols:6});
console.log(dashboardCheck.ndjson);
const errors = await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",options:{useRegex:true,maxResults:100},summary:"final formula error scan"});
console.log(errors.ndjson);
await fs.mkdir(outputDir,{recursive:true});
const preview = await wb.render({sheetName:"Dashboard",range:"A1:N38",scale:1.2,format:"png"});
await fs.writeFile(path.join(outputDir,"dashboard_preview.png"),new Uint8Array(await preview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(path.join(outputDir,"JK_Retail_Intelligence_MVP.xlsx"));
console.log("Workbook exported.");
