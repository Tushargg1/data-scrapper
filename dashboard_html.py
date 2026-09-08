import json

def get_dashboard_html(stats: dict, businesses: list, db_engine: str, app_name: str, app_version: str) -> str:
    biz_json = json.dumps(businesses, ensure_ascii=False)
    
    total_leads = stats.get('total_businesses', len(businesses))
    with_phone = stats.get('businesses_with_phone', 0)
    with_web = stats.get('businesses_with_website', 0)
    
    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{app_name} — Cloud Portal</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Inter', sans-serif; }}
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: #0f172a; }}
    ::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #475569; }}
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">

  <!-- Top Navigation -->
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <span class="text-2xl">⚡</span>
        <div>
          <span class="font-bold text-lg text-white">{app_name}</span>
          <span class="text-xs ml-2 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono">v{app_version}</span>
        </div>
      </div>
      <div class="flex items-center space-x-3">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-950 border border-emerald-800 text-emerald-300">
          <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
          DB: {db_engine.upper()} (Aiven Cloud)
        </span>
        <a href="https://data-scrapper-n7ua.onrender.com" target="_blank" class="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-lg shadow-emerald-500/20 transition-all flex items-center gap-1.5">
          <span>🚀</span> Open Streamlit Scraper
        </a>
        <a href="/docs" class="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-3 py-2 rounded-lg border border-slate-700 transition">
          📖 API Docs
        </a>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

    <!-- Hero Banner with Direct Access -->
    <div class="bg-gradient-to-br from-slate-900 via-slate-850 to-indigo-950/40 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
      <div class="absolute -right-16 -top-16 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div class="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="space-y-2">
          <div class="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-medium">
            <span>✨</span> Multi-Profile Google Maps Scraping & Lead Delivery Platform
          </div>
          <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Live Lead Extraction Dashboard
          </h1>
          <p class="text-slate-400 text-sm max-w-2xl leading-relaxed">
            This backend API connects to your central Aiven MySQL database. To run live element-based Google Maps scrapers by state, pincode, and custom niche, launch the full interactive Streamlit interface on Render.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-3 shrink-0">
          <a href="https://data-scrapper-n7ua.onrender.com" target="_blank" class="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm px-5 py-3 rounded-xl shadow-xl shadow-emerald-500/25 transition-all flex items-center gap-2">
            <span>🚀</span> Launch Streamlit Scraper UI
          </a>
          <a href="/docs" class="bg-slate-800 hover:bg-slate-750 text-white font-medium text-sm px-4 py-3 rounded-xl border border-slate-700 transition flex items-center gap-2">
            <span>📚</span> Swagger Docs
          </a>
          <a href="/api/info" class="bg-slate-900 hover:bg-slate-800 text-slate-400 font-medium text-xs px-3 py-3 rounded-xl border border-slate-800 transition">
            JSON Root
          </a>
        </div>
      </div>
    </div>

    <!-- Stats KPI Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition">
        <div class="flex items-center justify-between">
          <span class="text-slate-400 text-xs font-medium uppercase tracking-wider">Total Leads</span>
          <span class="text-emerald-400 text-lg">🏢</span>
        </div>
        <div class="mt-2 text-3xl font-bold text-white">{total_leads}</div>
        <div class="mt-1 text-xs text-slate-500">Synced with Aiven MySQL</div>
      </div>

      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition">
        <div class="flex items-center justify-between">
          <span class="text-slate-400 text-xs font-medium uppercase tracking-wider">With Phone Number</span>
          <span class="text-blue-400 text-lg">📞</span>
        </div>
        <div class="mt-2 text-3xl font-bold text-white">{with_phone}</div>
        <div class="mt-1 text-xs text-slate-500">Ready for calling & outreach</div>
      </div>

      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition">
        <div class="flex items-center justify-between">
          <span class="text-slate-400 text-xs font-medium uppercase tracking-wider">With Website</span>
          <span class="text-purple-400 text-lg">🌐</span>
        </div>
        <div class="mt-2 text-3xl font-bold text-white">{with_web}</div>
        <div class="mt-1 text-xs text-slate-500">Websites verified</div>
      </div>

      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition">
        <div class="flex items-center justify-between">
          <span class="text-slate-400 text-xs font-medium uppercase tracking-wider">Lead Delivery</span>
          <span class="text-amber-400 text-lg">📦</span>
        </div>
        <div class="mt-2 text-3xl font-bold text-emerald-400">10-Batch API</div>
        <div class="mt-1 text-xs text-slate-500">Atomic zero-duplicate delivery</div>
      </div>
    </div>

    <!-- Data Explorer Table -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
      <div class="p-5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            <span>📋</span> Real-Time Database Explorer
          </h2>
          <p class="text-xs text-slate-400 mt-0.5">Browse leads stored directly inside Aiven Cloud MySQL</p>
        </div>
        <div class="flex items-center gap-3">
          <input
            type="text"
            id="searchInput"
            placeholder="🔍 Search by name, niche, phone, state..."
            class="bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 w-64 sm:w-80 transition"
          />
          <span id="leadCountBadge" class="text-xs bg-slate-800 text-slate-300 px-2.5 py-1.5 rounded-lg border border-slate-700 font-mono">
            {len(businesses)} leads
          </span>
        </div>
      </div>

      <!-- Table Container -->
      <div class="overflow-x-auto max-h-[560px]">
        <table class="w-full text-left border-collapse text-xs">
          <thead class="bg-slate-950/80 text-slate-400 sticky top-0 z-10 border-b border-slate-800">
            <tr>
              <th class="p-3.5 font-semibold">Business Name</th>
              <th class="p-3.5 font-semibold">Niche</th>
              <th class="p-3.5 font-semibold">Location</th>
              <th class="p-3.5 font-semibold">Primary Phone</th>
              <th class="p-3.5 font-semibold">Phone 2</th>
              <th class="p-3.5 font-semibold">Rating / Reviews</th>
              <th class="p-3.5 font-semibold">Website</th>
              <th class="p-3.5 font-semibold">Maps Link</th>
            </tr>
          </thead>
          <tbody id="leadsTableBody" class="divide-y divide-slate-800/60 text-slate-300">
            <!-- Populated by script -->
          </tbody>
        </table>
      </div>
      <div class="p-4 border-t border-slate-800 bg-slate-950/60 text-xs text-slate-500 flex items-center justify-between">
        <span>Showing leads loaded directly from Aiven Cloud MySQL database.</span>
        <a href="https://data-scrapper-n7ua.onrender.com" target="_blank" class="text-emerald-400 hover:text-emerald-300 font-medium">Open Streamlit for full CSV/Excel export →</a>
      </div>
    </div>

    <!-- API Quick Reference Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 class="text-sm font-bold text-white flex items-center gap-2 mb-2">
          <span>📦</span> 10-Batch Lead Distribution
        </h3>
        <p class="text-xs text-slate-400 mb-3">Each user gets 10 fresh, non-repeating leads atomically marked in the database:</p>
        <pre class="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-emerald-400 font-mono overflow-x-auto">curl -H "X-User-Code: YOUR_CODE" \\
  "https://data-scrapper-henna.vercel.app/api/data/batch"</pre>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 class="text-sm font-bold text-white flex items-center gap-2 mb-2">
          <span>👥</span> User Registration
        </h3>
        <p class="text-xs text-slate-400 mb-3">New users register their user code for admin approval:</p>
        <pre class="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-indigo-300 font-mono overflow-x-auto">curl -X POST "https://data-scrapper-henna.vercel.app/api/users/register" \\
  -H "Content-Type: application/json" \\
  -d '{{"username":"Tushar","phone_number":"9999999999","user_code":"TUSH1"}}'</pre>
      </div>
    </div>

  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-800 bg-slate-950 py-6 text-center text-xs text-slate-500">
    <p>{app_name} • Cloud Hosted on Vercel & Render • Central Aiven MySQL Database</p>
  </footer>

  <script>
    const businesses = {biz_json};

    function renderRows(list) {{
      const tbody = document.getElementById('leadsTableBody');
      const badge = document.getElementById('leadCountBadge');
      badge.textContent = list.length + ' leads';

      if (list.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="8" class="p-8 text-center text-slate-500">No leads match your search query.</td></tr>';
        return;
      }}

      let html = '';
      for (const b of list) {{
        const name = b.name || b.Name || 'N/A';
        const niche = b.niche || b.Niche || 'N/A';
        const pincode = b.pincode || b.Pincode || '';
        const state = b.state || b.State || '';
        const phone = b.phone || b.Phone || b['Phone 1'] || 'N/A';
        const phone2 = b.phone_2 || b['Phone 2'] || '';
        const rating = b.rating || b.Rating || 'N/A';
        const reviews = b.reviews || b.Reviews || '';
        const web = b.website_link || b['Website Link'] || '';
        const maps = b.maps_url || b['Google Maps URL'] || '';

        const phoneHtml = (phone !== 'N/A' && phone !== '') 
          ? '<a href="tel:' + phone + '" class="text-emerald-400 hover:underline font-mono font-medium">' + phone + '</a>' 
          : '<span class="text-slate-600">—</span>';

        const phone2Html = phone2 ? '<span class="text-slate-400 font-mono">' + phone2 + '</span>' : '<span class="text-slate-600">—</span>';

        const webHtml = (web && web !== 'N/A')
          ? '<a href="' + web + '" target="_blank" class="text-blue-400 hover:underline truncate block max-w-[130px]">🔗 Visit</a>'
          : '<span class="text-slate-600">—</span>';

        const mapsHtml = maps 
          ? '<a href="' + maps + '" target="_blank" class="text-indigo-400 hover:underline">🗺️ View</a>' 
          : '<span class="text-slate-600">—</span>';

        html += '<tr class="hover:bg-slate-850/50 transition">' +
          '<td class="p-3.5 font-semibold text-white">' + name + '</td>' +
          '<td class="p-3.5"><span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">' + niche + '</span></td>' +
          '<td class="p-3.5 text-slate-400">' + pincode + (state ? ', ' + state : '') + '</td>' +
          '<td class="p-3.5">' + phoneHtml + '</td>' +
          '<td class="p-3.5">' + phone2Html + '</td>' +
          '<td class="p-3.5 text-amber-400 font-medium">★ ' + rating + ' <span class="text-slate-500 font-normal">(' + reviews + ')</span></td>' +
          '<td class="p-3.5">' + webHtml + '</td>' +
          '<td class="p-3.5">' + mapsHtml + '</td>' +
        '</tr>';
      }}
      tbody.innerHTML = html;
    }}

    // Initial render
    renderRows(businesses);

    // Search filter
    document.getElementById('searchInput').addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase().trim();
      if (!q) {{
        renderRows(businesses);
        return;
      }}
      const filtered = businesses.filter(b => {{
        const text = [
          b.name, b.Name,
          b.niche, b.Niche,
          b.phone, b.Phone, b['Phone 1'],
          b.phone_2, b['Phone 2'],
          b.pincode, b.Pincode,
          b.state, b.State
        ].filter(Boolean).join(' ').toLowerCase();
        return text.includes(q);
      }});
      renderRows(filtered);
    }});
  </script>

</body>
</html>"""
