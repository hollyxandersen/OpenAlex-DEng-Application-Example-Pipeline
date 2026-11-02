
"""
Generate an interactive research landscape dashboard from DuckDB.

Executes the analytical SQL queries stored in sql/, prepares the results
for presentation and generates a standalone HTML report.

The dashboard includes publication trends, researcher and institution
rankings, a geographic map and a searchable publication catalogue.
Analytical transformations remain separate from presentation logic.
"""


from datetime import date
from pathlib import Path
import json

import duckdb
import pandas as pd
import pycountry
from plotly.offline import get_plotlyjs


ROOT = Path(__file__).resolve().parent
DB = ROOT / "openalex.duckdb"
OUTPUT = ROOT / "output" / "research_landscape.html"

SQL_FILES = {
    "trends": "publication_trends.sql",
    "authors": "authors.sql",
    "institutions": "institutions.sql",
    "journals": "journals.sql",
    "topics": "topics.sql",
    "countries": "countries.sql",
    "papers": "enriched_works.sql",
}

METRICS = ["publication_count", "total_citations", "average_fwci"]


def records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def load_data():
    if not DB.is_file():
        raise FileNotFoundError("Run build_database.py first.")

    with duckdb.connect(str(DB), read_only=True) as con:
        tables = {}
        for name, filename in SQL_FILES.items():
            sql = (ROOT / "sql" / filename).read_text(encoding="utf-8")
            tables[name] = con.execute(sql).df()

    papers = tables["papers"]
    if len(papers) != papers["work_id"].nunique():
        raise ValueError("The paper catalogue contains duplicate work IDs.")

    trends = tables["trends"].copy()
    trends["year"] = pd.to_numeric(trends["year"], errors="coerce")
    trends = trends[
        trends["year"].notna()
        & (trends["year"] < date.today().year)
    ].sort_values("year")

    journals = tables["journals"].copy()
    if "source_type" in journals.columns:
        journals = journals[journals["source_type"] == "journal"]

    countries = tables["countries"].copy()

    def iso3(code):
        if pd.isna(code):
            return None
        country = pycountry.countries.get(alpha_2=str(code).upper())
        return country.alpha_3 if country else None

    countries["iso3"] = countries["country_code"].map(iso3)

    output = {
        "trends": records(trends),
        "papers": records(papers),
        "topics": records(tables["topics"]),
        "countries": records(countries.dropna(subset=["iso3"])),
    }

    for key, label, frame in [
        ("authors", "author_name", tables["authors"]),
        ("institutions", "institution_name", tables["institutions"]),
        ("journals", "source_name", journals),
    ]:
        requested = [
            label,
            *METRICS,
            "papers_with_fwci",
            "orcid",
            "institutions",
            "countries",
            "country_code",
            "institution_type",
            "source_type",
            "subfield_name",
            "author_id",
            "institution_id",
            "source_id",
        ]
        columns = list(dict.fromkeys(
            col for col in requested if col in frame.columns
        ))
        output[key] = records(frame[columns].dropna(subset=[label]))

    output["kpis"] = {
        "papers": len(papers),
        "authors": len(tables["authors"]),
        "institutions": len(tables["institutions"]),
        "countries": tables["countries"]["country_code"].nunique(),
    }

    return output


HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Photoactive Battery Research</title>

<style>
:root {
    --bg: #f5f8f7;
    --card: #ffffff;
    --ink: #20363e;
    --muted: #71858a;
    --line: #dce7e4;
    --teal: #468e89;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font: 13px "Segoe UI", Arial, sans-serif;
}

.dashboard {
    height: 100dvh;
    min-height: 610px;
    max-width: 1900px;
    margin: auto;
    padding: 12px 18px;
    display: grid;
    grid-template-rows:
        auto auto
        minmax(190px, 34fr)
        minmax(240px, 56fr)
        auto;
    gap: 10px;
}

header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
}

h1 {
    margin: 3px 0;
    font-size: clamp(23px, 2vw, 34px);
    letter-spacing: -0.7px;
}

h2 { font-size: 14px; margin: 0; }

.eyebrow {
    font-size: 10px;
    letter-spacing: 1.7px;
    font-weight: 700;
    color: var(--teal);
}

.subtitle {
    margin: 0;
    color: var(--muted);
    font-size: 11px;
}

button, input, select { font: inherit; }
button { cursor: pointer; }

.metric-switch {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}

.metric-switch span {
    color: var(--muted);
    font-size: 11px;
    margin-right: 4px;
}

.metric-btn, .small-btn, select {
    border: 1px solid var(--line);
    background: white;
    border-radius: 7px;
    padding: 7px 10px;
    color: var(--ink);
}

.metric-btn.active {
    background: var(--teal);
    color: white;
    border-color: var(--teal);
}

.kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
}

.kpi, .panel {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 11px;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
}

.kpi { padding: 9px 14px; }

.kpi strong {
    display: block;
    font-size: 21px;
    color: var(--teal);
}

.kpi span {
    color: var(--muted);
    font-size: 11px;
}

/* Four ranked charts */

.ranks {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    min-height: 0;
}

.rank-panel {
    display: flex;
    flex-direction: column;
}

.panel-head {
    padding: 10px 12px 6px;
    flex-shrink: 0;
}

.panel-head p {
    color: var(--muted);
    font-size: 10px;
    margin: 4px 0 0;
}

.rank-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: thin;
    overscroll-behavior: contain;
}

.rank-plot {
    padding: 3px 10px;
}

.rank-row {
    display: grid;
    grid-template-columns: minmax(0, 43%) minmax(0, 57%);
    gap: 8px;
    align-items: center;
    min-height: 34px;
    cursor: default;
}

.rank-name {
    min-width: 0;
    font-size: 11px;
    line-height: 1.25;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.rank-track {
    height: 22px;
    border-left: 1px solid #a9beb9;
    background: repeating-linear-gradient(
        to right,
        transparent 0,
        transparent calc(25% - 1px),
        #edf2f0 calc(25% - 1px),
        #edf2f0 25%
    );
}

.rank-bar {
    height: 100%;
    background: var(--teal);
}

.rank-row:hover .rank-bar,
.rank-row:focus .rank-bar {
    background: #2e746e;
}

.rank-row:focus-visible {
    outline: 2px solid var(--teal);
    border-radius: 4px;
}

/* Fixed numeric axis beneath scrollable bars */

.rank-axis {
    flex-shrink: 0;
    display: grid;
    grid-template-columns: minmax(0, 43%) minmax(0, 57%);
    gap: 8px;
    padding: 5px 20px 8px 10px;
    border-top: 1px solid var(--line);
    color: var(--muted);
    font-size: 10px;
}

.rank-axis-values {
    display: flex;
    justify-content: space-between;
    border-top: 1px solid #b7cac5;
    padding-top: 3px;
}

.rank-axis-title {
    text-align: center;
    font-size: 9px;
    margin-top: 2px;
}

/* Other dashboard panels */

.main-area {
    display: grid;
    grid-template-columns: minmax(260px, 31%) minmax(0, 1fr);
    gap: 10px;
    min-height: 0;
}

.left-stack {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
}

.trend-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.trend-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
}

.plot-fill {
    flex: 1;
    min-height: 0;
    width: 100%;
}

.map-panel {
    display: none;
    flex: 1;
    min-height: 0;
    flex-direction: column;
}

.left-stack.map-open .map-panel {
    display: flex;
}

.map-toggle {
    align-self: flex-start;
    flex-shrink: 0;
}

/* Paper catalogue */

.catalogue {
    display: flex;
    flex-direction: column;
}

.table-tools {
    display: flex;
    gap: 8px;
    padding: 6px 12px;
    border-bottom: 1px solid var(--line);
}

input[type=search] {
    flex: 1;
    min-width: 50px;
    border: 1px solid var(--line);
    border-radius: 7px;
    padding: 8px;
    color: var(--ink);
}

.count {
    font-size: 10px;
    color: var(--muted);
    padding: 4px 12px;
}

.papers {
    flex: 1;
    min-height: 0;
    overflow: auto;
}

.paper {
    border-bottom: 1px solid var(--line);
}

.paper summary {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 65px 65px;
    gap: 9px;
    padding: 10px 12px;
    align-items: center;
    cursor: pointer;
    list-style: none;
}

.paper summary::-webkit-details-marker {
    display: none;
}

.paper summary:hover {
    background: #f8fbfa;
}

.paper-name {
    font-weight: 600;
    line-height: 1.35;
}

.paper-sub {
    color: var(--muted);
    font-size: 10px;
    margin-top: 4px;
}

.paper-num {
    text-align: right;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
}

.paper-num small {
    display: block;
    font-size: 9px;
    color: var(--muted);
}

.paper-extra {
    background: #f8fbfa;
    padding: 8px 13px;
    font-size: 11px;
    line-height: 1.5;
    overflow-wrap: anywhere;
}

.paper-extra p { margin: 6px 0; }

a { color: var(--teal); }

.pager {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 12px;
    padding: 7px;
    border-top: 1px solid var(--line);
    font-size: 11px;
}

.pager button { padding: 5px 9px; }
.pager button:disabled { opacity: 0.4; cursor: default; }

footer {
    font-size: 9px;
    color: var(--muted);
    line-height: 1.25;
}

/* A one-screen dashboard on desktop,
   normal scrolling where screens are smaller */

@media (max-width: 1100px), (max-height: 680px) {
    .dashboard {
        height: auto;
        min-height: 100vh;
        grid-template-rows: auto auto auto auto auto;
    }

    .ranks { min-height: 270px; }

    .rank-scroll {
        flex: none;
        height: 230px;
    }

    .main-area { min-height: 500px; }
    .papers { max-height: 480px; }

    .plot-fill {
        flex: none;
        height: 280px;
    }
}

@media (max-width: 780px) {
    header {
        align-items: flex-start;
        flex-direction: column;
    }

    .ranks {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .main-area {
        grid-template-columns: 1fr;
    }

    .kpis {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 440px) {
    .dashboard { padding: 9px; }
    .ranks { grid-template-columns: 1fr; }

    .paper summary {
        grid-template-columns: minmax(0, 1fr) 51px 47px;
    }
}
</style>

<script>__PLOTLY__</script>
</head>

<body>
<main class="dashboard">

<header>
    <div>
        <div class="eyebrow">OPENALEX · RESEARCH LANDSCAPE</div>
        <h1>Photoactive Battery Research</h1>
        <p class="subtitle">
            A bibliometric overview of research related to photoactive batteries.
        </p>
    </div>

    <div class="metric-switch">
        <span>Rank by</span>
        <button class="metric-btn active" data-metric="publication_count">
            Publications
        </button>
        <button class="metric-btn" data-metric="total_citations">
            Citations
        </button>
        <button class="metric-btn" data-metric="average_fwci">
            Avg. FWCI
        </button>
    </div>
</header>

<section class="kpis">
    <div class="kpi">
        <strong id="kp-papers"></strong>
        <span>Publications</span>
    </div>
    <div class="kpi">
        <strong id="kp-authors"></strong>
        <span>Identified researchers</span>
    </div>
    <div class="kpi">
        <strong id="kp-institutions"></strong>
        <span>Represented institutions</span>
    </div>
    <div class="kpi">
        <strong id="kp-countries"></strong>
        <span>Countries</span>
    </div>
</section>

<section class="ranks">
    <article class="panel rank-panel">
        <div class="panel-head">
            <h2>Top institutions</h2>
            <p>Hover for country and impact</p>
        </div>
        <div class="rank-scroll">
            <div id="chart-institutions" class="rank-plot"></div>
        </div>
        <div id="axis-institutions" class="rank-axis"></div>
    </article>

    <article class="panel rank-panel">
        <div class="panel-head">
            <h2>Top authors</h2>
            <p>Hover for affiliations and impact</p>
        </div>
        <div class="rank-scroll">
            <div id="chart-authors" class="rank-plot"></div>
        </div>
        <div id="axis-authors" class="rank-axis"></div>
    </article>

    <article class="panel rank-panel">
        <div class="panel-head">
            <h2>Top journals</h2>
            <p>Publication venues</p>
        </div>
        <div class="rank-scroll">
            <div id="chart-journals" class="rank-plot"></div>
        </div>
        <div id="axis-journals" class="rank-axis"></div>
    </article>

    <article class="panel rank-panel">
        <div class="panel-head">
            <h2>Top topics</h2>
            <p>OpenAlex classifications · by papers</p>
        </div>
        <div class="rank-scroll">
            <div id="chart-topics" class="rank-plot"></div>
        </div>
        <div id="axis-topics" class="rank-axis"></div>
    </article>
</section>

<section class="main-area">

    <div class="left-stack" id="left-stack">
        <article class="panel trend-panel">
            <div class="panel-head trend-head">
                <div>
                    <h2>Research through time</h2>
                    <p>Annual publication and citation activity</p>
                </div>

                <select id="trend-type" aria-label="Timeline metric">
                    <option value="publication_count">Publications</option>
                    <option value="citation_count">Citations received</option>
                </select>
            </div>

            <div id="chart-trend" class="plot-fill"></div>
        </article>

        <button id="map-toggle"
                class="small-btn map-toggle"
                aria-expanded="false">
            Explore country map ▾
        </button>

        <article class="panel map-panel" id="map-panel">
            <div class="panel-head">
                <h2>Research geography</h2>
                <p>Country affiliations · selected metric</p>
            </div>
            <div id="chart-map" class="plot-fill"></div>
        </article>
    </div>

    <article class="panel catalogue">
        <div class="panel-head">
            <h2>Explore the papers</h2>
            <p>Search, sort and expand to view publication details</p>
        </div>

        <div class="table-tools">
            <input type="search"
                   id="paper-search"
                   placeholder="Search title, author, institution, topic…"
                   aria-label="Search papers">

            <select id="paper-sort">
                <option value="year">Newest</option>
                <option value="citations">Most cited</option>
                <option value="fwci">Highest FWCI</option>
                <option value="relevance">Most relevant</option>
                <option value="title">Title A–Z</option>
            </select>
        </div>

        <div id="count" class="count"></div>
        <div id="papers" class="papers"></div>

        <div class="pager">
            <button id="prev" class="small-btn">Previous</button>
            <span id="paging"></span>
            <button id="next" class="small-btn">Next</button>
        </div>
    </article>
</section>

<footer>
    OpenAlex search: “photoactive battery”.
    Metrics describe retrieved publications, not complete researcher or institutional output.
    Country counts may overlap. FWCI does not measure search relevance.
    Annual citation histories may be incomplete.
    Current year excluded from trends.
    · Generated __DATE__
</footer>

</main>

<script id="data" type="application/json">__DATA__</script>

<script>
const D = JSON.parse(document.getElementById("data").textContent);

const teal = "#468e89";
const muted = "#71858a";
const grid = "#e9efed";

let metric = "publication_count";
let page = 0;
const perPage = 20;

const labels = {
    publication_count: "Publications",
    total_citations: "Citations",
    average_fwci: "Average FWCI"
};

const fmt = (value, decimals = 0) =>
    value == null ? "—" :
    Number(value).toLocaleString("en-GB", {
        maximumFractionDigits: decimals
    });

const esc = value => String(value ?? "").replace(
    /[&<>"']/g,
    char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]
);

function link(url, label) {
    try {
        const parsed = new URL(url);
        if (!["http:", "https:"].includes(parsed.protocol)) return "—";

        return `<a href="${esc(parsed.href)}"
                   target="_blank" rel="noopener noreferrer">
                   ${esc(label)}
                </a>`;
    } catch {
        return "—";
    }
}

const plotConfig = {
    responsive: true,
    displayModeBar: false,
    displaylogo: false
};

const basePlot = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: {
        family: "Segoe UI,Arial",
        size: 10,
        color: muted
    },
    showlegend: false
};

// KPI totals

for (const key of ["papers", "authors", "institutions", "countries"]) {
    document.getElementById("kp-" + key).textContent =
        fmt(D.kpis[key]);
}

// Full detail text on hover or keyboard focus

function hoverText(row, field) {
    const lines = [
        String(row[field] ?? ""),
        `Publications: ${fmt(row.publication_count)}`
    ];

    if (row.total_citations != null) {
        lines.push(`Citations: ${fmt(row.total_citations)}`);
    }

    if (row.average_fwci != null) {
        lines.push(`Average FWCI: ${fmt(row.average_fwci, 2)}`);
    }

    if (row.papers_with_fwci != null) {
        lines.push(`Papers with FWCI: ${fmt(row.papers_with_fwci)}`);
    }

    for (const [key, title] of [
        ["institutions", "Institutions"],
        ["countries", "Countries"],
        ["country_code", "Country"],
        ["institution_type", "Type"],
        ["source_type", "Source"],
        ["subfield_name", "Subfield"],
        ["orcid", "ORCID"]
    ]) {
        if (row[key]) {
            lines.push(`${title}: ${row[key]}`);
        }
    }

    return lines.join("\n");
}

// HTML/CSS bars: labels and bars scroll together.
// Numeric axes are separate and stay visible.

function rank(which, nameField, metricField) {
    const rows = D[which]
        .filter(row =>
            row[nameField] &&
            row[metricField] != null &&
            Number.isFinite(Number(row[metricField]))
        )
        .sort((a, b) => Number(b[metricField]) - Number(a[metricField]))
        .slice(0, 20);

    const maximum = Math.max(
        1,
        ...rows.map(row => Number(row[metricField]))
    );

    const chart = document.getElementById("chart-" + which);

    chart.innerHTML = rows.map(row => {
        const value = Number(row[metricField]);
        const width = Math.max(
            0,
            Math.min(100, 100 * value / maximum)
        );

        const tooltip = hoverText(row, nameField);

        return `
            <div class="rank-row" tabindex="0"
                 title="${esc(tooltip)}">
                <div class="rank-name">
                    ${esc(row[nameField])}
                </div>
                <div class="rank-track">
                    <div class="rank-bar"
                         style="width:${width}%"></div>
                </div>
            </div>
        `;
    }).join("");

    const decimals = metricField === "average_fwci" ? 2 : 0;

    document.getElementById("axis-" + which).innerHTML = `
        <div></div>
        <div>
            <div class="rank-axis-values">
                <span>0</span>
                <span>${fmt(maximum / 2, decimals)}</span>
                <span>${fmt(maximum, decimals)}</span>
            </div>
            <div class="rank-axis-title">
                ${esc(labels[metricField] || "Publications")}
            </div>
        </div>
    `;
}

function drawRankings() {
    rank("institutions", "institution_name", metric);
    rank("authors", "author_name", metric);
    rank("journals", "source_name", metric);
    rank("topics", "topic_name", "publication_count");
}

// Publication timeline

function drawTrend() {
    const column = document.getElementById("trend-type").value;

    const rows = D.trends
        .filter(row =>
            row.year != null &&
            row[column] != null &&
            (column !== "citation_count" || row.year >= 2013)
        )
        .sort((a, b) => a.year - b.year);

    Plotly.react("chart-trend", [{
        type: "scatter",
        mode: "lines+markers",
        x: rows.map(row => row.year),
        y: rows.map(row => row[column]),
        line: {color: teal, width: 3},
        marker: {size: 5},
        hovertemplate: "%{x}<br>%{y:,.0f}<extra></extra>"
    }], {
        ...basePlot,
        autosize: true,
        margin: {l: 52, r: 16, t: 10, b: 32},
        xaxis: {
            title: "Year",
            tickformat: "d",
            gridcolor: grid
        },
        yaxis: {
            title: column === "citation_count"
                ? "Citations"
                : "Publications",
            gridcolor: grid
        }
    }, plotConfig);
}

// Optional country map

function drawMap() {
    const rows = D.countries.filter(
        row => row.iso3 && row[metric] != null
    );

    Plotly.react("chart-map", [{
        type: "choropleth",
        locationmode: "ISO-3",
        locations: rows.map(row => row.iso3),
        z: rows.map(row => row[metric]),
        text: rows.map(row => row.country_code),
        colorscale: [
            [0, "#e6f2ee"],
            [1, "#397e7a"]
        ],
        marker: {
            line: {color: "#fff", width: 0.3}
        },
        colorbar: {
            thickness: 8,
            len: 0.6,
            outlinewidth: 0
        },
        hovertemplate: "%{text}: %{z:,.2f}<extra></extra>"
    }], {
        ...basePlot,
        autosize: true,
        margin: {l: 0, r: 0, t: 0, b: 0},
        geo: {
            projection: {type: "natural earth"},
            showframe: false,
            showcoastlines: false,
            showland: true,
            landcolor: "#e9efed",
            bgcolor: "rgba(0,0,0,0)"
        }
    }, plotConfig);
}

// Metric selection

for (const button of document.querySelectorAll("[data-metric]")) {
    button.addEventListener("click", () => {
        metric = button.dataset.metric;

        document.querySelectorAll("[data-metric]").forEach(item => {
            item.classList.toggle("active", item === button);
        });

        drawRankings();

        if (document.getElementById("left-stack")
                    .classList.contains("map-open")) {
            drawMap();
        }
    });
}

document.getElementById("trend-type").addEventListener(
    "change",
    drawTrend
);

document.getElementById("map-toggle").addEventListener(
    "click",
    () => {
        const stack = document.getElementById("left-stack");
        const open = stack.classList.toggle("map-open");
        const button = document.getElementById("map-toggle");

        button.textContent = open
            ? "Hide country map ▴"
            : "Explore country map ▾";

        button.setAttribute("aria-expanded", String(open));

        requestAnimationFrame(() => {
            drawTrend();
            if (open) drawMap();
        });
    }
);

// Searchable, expandable publication catalogue

function drawCatalogue() {
    const query = document.getElementById("paper-search")
        .value.toLowerCase().trim();

    const order = document.getElementById("paper-sort").value;

    const sortFields = {
        year: "publication_year",
        citations: "cited_by_count",
        fwci: "fwci",
        relevance: "relevance_score"
    };

    const rows = D.papers.filter(paper => {
        if (!query) return true;

        return [
            paper.title,
            paper.authors,
            paper.source_name,
            paper.institutions,
            paper.countries,
            paper.topics
        ].some(value =>
            String(value ?? "").toLowerCase().includes(query)
        );
    });

    rows.sort((a, b) => {
        if (order === "title") {
            return String(a.title ?? "").localeCompare(
                String(b.title ?? "")
            );
        }

        const key = sortFields[order];
        const x = a[key];
        const y = b[key];

        if (x == null) return y == null ? 0 : 1;
        if (y == null) return -1;

        return Number(y) - Number(x);
    });

    const pages = Math.max(1, Math.ceil(rows.length / perPage));
    page = Math.min(page, pages - 1);

    document.getElementById("count").textContent =
        `${fmt(rows.length)} matching papers`;

    document.getElementById("paging").textContent =
        `${page + 1} / ${pages}`;

    document.getElementById("prev").disabled = page === 0;
    document.getElementById("next").disabled = page === pages - 1;

    const visible = rows.slice(
        page * perPage,
        (page + 1) * perPage
    );

    document.getElementById("papers").innerHTML = visible.map(
        paper => `
        <details class="paper">
            <summary>
                <div>
                    <div class="paper-name">
                        ${esc(paper.title || "Untitled")}
                    </div>
                    <div class="paper-sub">
                        ${esc(paper.publication_year ?? "Year unknown")}
                        ·
                        ${esc(paper.source_name || "Unknown source")}
                    </div>
                </div>
                <div class="paper-num">
                    ${fmt(paper.cited_by_count)}
                    <small>Citations</small>
                </div>
                <div class="paper-num">
                    ${fmt(paper.fwci, 2)}
                    <small>FWCI</small>
                </div>
            </summary>

            <div class="paper-extra">
                <p><b>Authors (publication order):</b>
                    ${esc(paper.authors || "Not available")}</p>
                <p><b>Institutions:</b>
                    ${esc(paper.institutions || "Not available")}</p>
                <p><b>Countries:</b>
                    ${esc(paper.countries || "Not available")}</p>
                <p><b>Topics:</b>
                    ${esc(paper.topics || "Not available")}</p>
                <p><b>Publication date:</b>
                    ${esc(paper.publication_date || "Unknown")}
                    · <b>Search relevance:</b>
                    ${fmt(paper.relevance_score, 2)}</p>
                <p>
                    ${link(paper.doi, "DOI")}
                    · ${link(paper.work_id, "OpenAlex paper")}
                    · ${link(paper.source_id, "Publication source")}
                </p>
            </div>
        </details>
    `).join("") || "<p style='padding:15px'>No matching papers.</p>";
}

for (const id of ["paper-search", "paper-sort"]) {
    document.getElementById(id).addEventListener(
        id === "paper-search" ? "input" : "change",
        () => {
            page = 0;
            drawCatalogue();
        }
    );
}

document.getElementById("prev").addEventListener("click", () => {
    page--;
    drawCatalogue();
});

document.getElementById("next").addEventListener("click", () => {
    page++;
    drawCatalogue();
});

// Initial rendering

drawRankings();
drawTrend();
drawCatalogue();

const observer = new ResizeObserver(() => {
    Plotly.Plots.resize(document.getElementById("chart-trend"));

    if (document.getElementById("left-stack")
                .classList.contains("map-open")) {
        Plotly.Plots.resize(document.getElementById("chart-map"));
    }
});

observer.observe(document.getElementById("chart-trend"));

</script>
</body>
</html>
"""


def main():
    print("Reading analytical SQL marts...")
    data = load_data()

    payload = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":")
    ).replace("<", "\\u003c").replace("&", "\\u0026")

    html = (
        HTML.replace("__PLOTLY__", get_plotlyjs())
        .replace("__DATA__", payload)
        .replace("__DATE__", date.today().strftime("%d %B %Y"))
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")

    print(f"Report created: {OUTPUT}")
    print(f"Papers included: {len(data['papers']):,}")


if __name__ == "__main__":
    main()
