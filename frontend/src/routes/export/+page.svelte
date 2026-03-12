<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { Alert } from "flowbite-svelte";
  import { ArrowLeft, Download, CheckCircle, FileSpreadsheet, FileDown } from "lucide-svelte";

  const API_URL = "http://localhost:8000";

  let exportItems: any[] = [];
  let loading = true;
  let errorMsg = "";

  async function fetchConfirmedItems() {
    loading = true;
    errorMsg = "";
    try {
      const res = await fetch(`${API_URL}/confirmations`);
      if (!res.ok) throw new Error("Failed to load confirmed items");
      exportItems = await res.json();
      console.log("Loaded confirmed items:", exportItems);
    } catch (err) {
      console.error("Error fetching confirmed items:", err);
      errorMsg = "Fehler beim Laden der bestätigten Zuordnungen.";
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchConfirmedItems();
  });

  function handleBack() {
    goto("/results");
  }

  function handleNewAnalysis() {
    goto("/");
  }

  function exportToCSV() {
    if (exportItems.length === 0) {
      alert("Keine bestätigten Einträge zum Exportieren vorhanden.");
      return;
    }

    // Create CSV content
    const headers = [
      "Material-Nr.",
      "Kurzbeschreibung",
      "Bestelltext",
      "Cluster ID",
      "Cluster Name",
      "Zugewiesene Zollnummer",
      "Konfidenz",
      "Bestätigt am"
    ];

    const rows = exportItems.map(item => [
      item.material_number,
      item.short_text || "",
      (item.purchase_order_text || "").replace(/\n/g, " "),
      item.cluster_id,
      item.cluster_name,
      item.assigned_tariff_code,
      item.confidence_score ? (item.confidence_score * 100).toFixed(1) + "%" : "N/A",
      new Date(item.confirmed_at).toLocaleString("de-DE")
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(","))
    ].join("\n");

    // Create and trigger download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    
    link.setAttribute("href", url);
    link.setAttribute("download", `hs_code_export_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = "hidden";
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function exportToJSON() {
    if (exportItems.length === 0) {
      alert("Keine bestätigten Einträge zum Exportieren vorhanden.");
      return;
    }

    const jsonContent = JSON.stringify(exportItems, null, 2);
    const blob = new Blob([jsonContent], { type: "application/json;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    
    link.setAttribute("href", url);
    link.setAttribute("download", `hs_code_export_${new Date().toISOString().split('T')[0]}.json`);
    link.style.visibility = "hidden";
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  $: totalItems = exportItems.length;
  $: uniqueClusters = new Set(exportItems.map(item => item.cluster_id)).size;
</script>

<div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
  <div class="max-w-7xl mx-auto px-8 py-12">
    <!-- Header -->
    <div class="mb-12">
      <div class="flex items-center gap-3 mb-3">
        <button
          on:click={handleBack}
          class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-gray-300 bg-white hover:bg-gray-50 h-9 px-3"
        >
          <ArrowLeft class="h-4 w-4 mr-2" />
          Zurück zu Ergebnissen
        </button>
      </div>
      <h1 class="text-4xl text-[#BB1E38] font-bold mb-2">Export & Abschluss</h1>
      <p class="text-base text-[#6b6b6b]">Bestätigte HS-Code-Zuordnungen exportieren</p>
    </div>

    {#if errorMsg}
      <Alert color="red" class="mb-8">{errorMsg}</Alert>
    {/if}

    {#if loading}
      <div class="flex justify-center items-center py-20">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#BB1E38]"></div>
      </div>
    {:else}
      <!-- Summary Stats -->
      <div class="grid md:grid-cols-3 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow-md p-6 border-l-4 border-green-500">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-600 font-medium">Bestätigte Artikel</p>
              <p class="text-3xl font-bold text-[#272425] mt-1">{totalItems}</p>
            </div>
            <CheckCircle class="h-12 w-12 text-green-500 opacity-80" />
          </div>
        </div>

        <div class="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-500">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-600 font-medium">Cluster</p>
              <p class="text-3xl font-bold text-[#272425] mt-1">{uniqueClusters}</p>
            </div>
            <div class="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center">
              <span class="text-2xl font-bold text-blue-600">C</span>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow-md p-6 border-l-4 border-[#BB1E38]">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-600 font-medium">Bereit zum Export</p>
              <p class="text-3xl font-bold text-[#272425] mt-1">✓</p>
            </div>
            <FileSpreadsheet class="h-12 w-12 text-[#BB1E38] opacity-80" />
          </div>
        </div>
      </div>

      <!-- Export Options -->
      <div class="bg-white rounded-xl shadow-lg p-8 mb-8">
        <h2 class="text-2xl font-semibold text-[#272425] mb-6">Export-Optionen</h2>
        
        {#if totalItems === 0}
          <div class="text-center py-12">
            <FileDown class="mx-auto h-16 w-16 text-gray-300 mb-4" />
            <p class="text-gray-500 text-lg mb-2">Keine bestätigten Einträge vorhanden</p>
            <p class="text-gray-400 text-sm mb-6">Bitte bestätigen Sie zunächst einige Zuordnungen auf der Ergebnisseite.</p>
            <button
              on:click={handleBack}
              class="inline-flex items-center justify-center rounded-md text-sm font-medium h-10 px-6 py-2 bg-[#BB1E38] hover:bg-[#9a1830] text-white"
            >
              Zu Ergebnissen
            </button>
          </div>
        {:else}
          <div class="grid md:grid-cols-2 gap-6">
            <!-- CSV Export -->
            <button
              on:click={exportToCSV}
              class="group relative overflow-hidden border-2 border-gray-200 rounded-lg p-8 hover:border-[#BB1E38] hover:shadow-lg transition-all"
            >
              <div class="relative z-10">
                <div class="flex items-center justify-between mb-4">
                  <FileSpreadsheet class="h-12 w-12 text-green-600" />
                  <Download class="h-8 w-8 text-gray-400 group-hover:text-[#BB1E38] transition-colors" />
                </div>
                <h3 class="text-xl font-bold text-[#272425] mb-2">CSV Export</h3>
                <p class="text-sm text-gray-600">
                  Exportieren Sie alle bestätigten Zuordnungen als CSV-Datei für Excel oder andere Tools.
                </p>
                <div class="mt-4 text-left">
                  <span class="inline-block px-3 py-1 bg-gray-100 rounded-full text-xs font-medium text-gray-700">
                    {totalItems} Einträge
                  </span>
                </div>
              </div>
              <div class="absolute inset-0 bg-gradient-to-br from-green-50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </button>

            <!-- JSON Export -->
            <button
              on:click={exportToJSON}
              class="group relative overflow-hidden border-2 border-gray-200 rounded-lg p-8 hover:border-[#BB1E38] hover:shadow-lg transition-all"
            >
              <div class="relative z-10">
                <div class="flex items-center justify-between mb-4">
                  <div class="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center">
                    <span class="text-2xl font-mono font-bold text-blue-600">&#123; &#125;</span>
                  </div>
                  <Download class="h-8 w-8 text-gray-400 group-hover:text-[#BB1E38] transition-colors" />
                </div>
                <h3 class="text-xl font-bold text-[#272425] mb-2">JSON Export</h3>
                <p class="text-sm text-gray-600">
                  Exportieren Sie die Daten als JSON für programmatische Weiterverarbeitung oder API-Integration.
                </p>
                <div class="mt-4 text-left">
                  <span class="inline-block px-3 py-1 bg-gray-100 rounded-full text-xs font-medium text-gray-700">
                    {totalItems} Einträge
                  </span>
                </div>
              </div>
              <div class="absolute inset-0 bg-gradient-to-br from-blue-50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </button>
          </div>
        {/if}
      </div>

      <!-- Preview Table -->
      {#if totalItems > 0}
        <div class="bg-white rounded-xl shadow-lg overflow-hidden mb-8">
          <div class="p-6 border-b border-gray-200 bg-gray-50">
            <h2 class="text-xl font-semibold text-[#272425]">Vorschau der Export-Daten</h2>
            <p class="text-sm text-gray-600 mt-1">Die ersten 10 Einträge</p>
          </div>
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Material-Nr.</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Beschreibung</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cluster</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">HS-Code</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Konfidenz</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bestätigt</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                {#each exportItems.slice(0, 10) as item}
                  <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-[#272425]">{item.material_number}</td>
                    <td class="px-6 py-4 text-sm text-gray-600 max-w-xs truncate">{item.short_text}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{item.cluster_name}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-mono font-semibold text-[#BB1E38]">{item.assigned_tariff_code}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                      {#if item.confidence_score}
                        <span class="px-2 py-1 rounded text-xs font-medium {item.confidence_score >= 0.8 ? 'bg-green-100 text-green-800' : item.confidence_score >= 0.5 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}">
                          {Math.round(item.confidence_score * 100)}%
                        </span>
                      {:else}
                        <span class="text-gray-400 text-xs">N/A</span>
                      {/if}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {new Date(item.confirmed_at).toLocaleDateString("de-DE")}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
          {#if totalItems > 10}
            <div class="px-6 py-4 bg-gray-50 border-t border-gray-200 text-center text-sm text-gray-600">
              ... und {totalItems - 10} weitere Einträge
            </div>
          {/if}
        </div>
      {/if}

      <!-- Actions -->
      <div class="flex justify-between items-center pt-6">
        <button
          on:click={handleBack}
          class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-gray-300 bg-white hover:bg-gray-50 h-10 px-6 py-2"
        >
          <ArrowLeft class="mr-2 h-4 w-4" />
          Zurück zu Ergebnissen
        </button>
        
        <button
          on:click={handleNewAnalysis}
          class="inline-flex items-center justify-center rounded-md text-sm font-medium h-10 px-6 py-2 bg-[#BB1E38] hover:bg-[#9a1830] text-white"
        >
          Neue Analyse starten
        </button>
      </div>
    {/if}
  </div>
</div>
