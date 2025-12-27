import csv
import io
import json

from flask import Blueprint, flash, redirect, render_template, request, send_file

from app.intelx_utils import search_intelx
from app.utils import (
    add_to_watchlist,
    check_breaches,
    clean_sources_light,
    generate_charts,
    load_json,
    merge_breach_sources,
    save_json,
    save_search,
)

WATCHLIST_FILE = "data/watchlist.json"


main = Blueprint("main", __name__)

@main.route("/", methods=["GET", "POST"])
def index():
    results = None
    error = None
    charts = {"timeline": None}

    if request.method == "POST":
        query = request.form.get("email")
        if query:
            data = check_breaches(query)

            if data.get("success"):
                # Clean LeakCheck results
                cleaned_sources = clean_sources_light(data["sources"])

                # Get IntelX results
                intelx_results = search_intelx(query)

                # Merge and sort
                merged_sources = merge_breach_sources(cleaned_sources, intelx_results)

                # Final output package
                data["sources"] = merged_sources  # Replaces with combined list
                results = data
                results["intelx"] = intelx_results
                results["query"] = query

                # Generate chart and save
                charts = generate_charts(data)
                save_search(query, data)
            else:
                error = data.get("error", "Something went wrong.")

    watchlist = load_json(WATCHLIST_FILE, [])
    return render_template("index.html", results=results, error=error, charts=charts, watchlist=watchlist)


@main.route("/export_csv", methods=["POST"])
def export_csv():
    # Get data from form
    sources = request.form.get("sources_json")
    query = request.form.get("query")

    if not sources or not query:
        return "Missing data", 400

    try:
        source_list = json.loads(sources)
    except json.JSONDecodeError:
        return "Invalid JSON", 400

    # Create in-memory CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Breach Name", "Date"])

    for breach in source_list:
        writer.writerow([breach.get("name", "Unknown"), breach.get("date", "N/A")])

    output.seek(0)

    filename = f"breach_report_{query.replace('@', '_at_')}.csv"
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )


@main.route("/add_to_watchlist", methods=["POST"])
def add_to_watchlist_route():
    query = request.form.get("query")
    if not query:
        flash("Missing query", "danger")
        return redirect("/")

    success = add_to_watchlist(query)
    if success:
        flash(f"✅ Added '{query}' to watchlist", "success")
    else:
        flash(f"⚠️ '{query}' is already in watchlist", "info")

    return redirect("/")


@main.route("/remove_from_watchlist", methods=["POST"])
def remove_from_watchlist():
    item = request.form.get("item")
    watchlist = load_json(WATCHLIST_FILE, [])

    if item in watchlist:
        watchlist.remove(item)
        save_json(WATCHLIST_FILE, watchlist)
        flash(f"❌ Removed '{item}' from watchlist", "warning")

    return redirect("/")
