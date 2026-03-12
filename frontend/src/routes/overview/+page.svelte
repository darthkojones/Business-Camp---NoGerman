<script context="module" lang="ts">
  // this route uses client‑only dependencies (chart.js), disable SSR/prerender
  export const prerender = false;
  export const ssr = false;
</script>

<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { afterNavigate } from "$app/navigation";
  import { goto } from "$app/navigation";
  import {
    Chart as ChartJS,
    Title,
    Tooltip,
    Legend,
    BarElement,
    BarController,
    CategoryScale,
    LinearScale,
    type ChartConfiguration,
  } from "chart.js";
  import { Search, CheckCircle, RefreshCw } from "lucide-svelte";
  import NavigationHeader from "$lib/components/NavigationHeader.svelte";
  import { Alert } from "flowbite-svelte";

  ChartJS.register(
    Title,
    Tooltip,
    Legend,
    BarElement,
    BarController,
    CategoryScale,
    LinearScale,
  );

  interface DistributionItem {
    tariff_code_id: number | null;
    goods_code: string | null;
    description: string | null;
    count: number;
  }

  interface Material {
    id: number;
    material_number: string;
    short_text: string | null;
    purchase_order_text: string | null;
    is_classified: boolean;
    tariff_code_id: number | null;
  }

  interface TariffCode {
    id: number;
    goods_code: string;
    description: string | null;
  }

  let distributionData: DistributionItem[] = [];
  let loadingDistribution = true;

  // export / summary state
  const API_URL = "http://localhost:8000";
  let exportItems: any[] = [];
  let loadingExport = true;
  let errorExport = "";

  let selectedCodeId: number | null = null;
  let selectedCodeInfo: DistributionItem | null = null;

  let materials: Material[] = [];
  let loadingMaterials = false;

  let allTariffs: TariffCode[] = [];
  let tariffSearchQuery = "";

  // Hierarchical selection state
  let hierarchyLevels: { items: TariffCode[]; selected: TariffCode | null }[] =
    [{ items: [], selected: null }];
  let loadingHierarchy = false;

  // Selection state
  let selectedMaterialIds: Set<number> = new Set();
  let targetTariffCodeId: number | null = null;
  let updating = false;

  async function fetchLevel(parentId: number | null, levelIndex: number) {
    loadingHierarchy = true;
    try {
      const url = parentId
        ? `http://localhost:8000/tariffs/hierarchy?parent_id=${parentId}`
        : "http://localhost:8000/tariffs/hierarchy";
      const res = await fetch(url);
      if (res.ok) {
        const items = await res.json();
        hierarchyLevels[levelIndex].items = items;
        hierarchyLevels = [...hierarchyLevels]; // trigger reactivity
      }
    } catch (e) {
      console.error("Failed to fetch hierarchy:", e);
    } finally {
      loadingHierarchy = false;
    }
  }

  async function handleHierarchySelect(
    levelIndex: number,
    item: TariffCode | null,
  ) {
    // Clear all levels below this one
    hierarchyLevels = hierarchyLevels.slice(0, levelIndex + 1);
    hierarchyLevels[levelIndex].selected = item;

    if (item) {
      targetTariffCodeId = item.id;
      // Pre-emptively add next level
      hierarchyLevels.push({ items: [], selected: null });
      await fetchLevel(item.id, levelIndex + 1);
      // If the new level has no items, it means we reached a leaf
      if (hierarchyLevels[levelIndex + 1].items.length === 0) {
        hierarchyLevels = hierarchyLevels.slice(0, levelIndex + 1);
      }
    } else {
      targetTariffCodeId =
        levelIndex > 0
          ? hierarchyLevels[levelIndex - 1].selected?.id || null
          : null;
    }
    hierarchyLevels = [...hierarchyLevels];
  }

  // --- export helpers --------------------------------------------------
  async function fetchConfirmedItems() {
    loadingExport = true;
    errorExport = "";
    try {
      const res = await fetch(`${API_URL}/confirmations`);
      if (!res.ok) throw new Error("Failed to load confirmed items");
      exportItems = await res.json();
    } catch (err) {
      console.error("Error fetching confirmed items:", err);
      errorExport = "Fehler beim Laden der bestätigten Zuordnungen.";
    } finally {
      loadingExport = false;
    }
  }

  function exportToCSV() {
    if (exportItems.length === 0) {
      alert("Keine bestätigten Einträge zum Exportieren vorhanden.");
      return;
    }

    const headers = [
      "Material-Nr.",
      "Kurzbeschreibung",
      "Bestelltext",
      "Cluster ID",
      "Cluster Name",
      "Zugewiesene Zollnummer",
      "Konfidenz",
      "Bestätigt am",
    ];

    const rows = exportItems.map((item) => [
      item.material_number,
      item.short_text || "",
      (item.purchase_order_text || "").replace(/\n/g, " "),
      item.cluster_id,
      item.cluster_name,
      item.assigned_tariff_code,
      item.confidence_score
        ? (item.confidence_score * 100).toFixed(1) + "%"
        : "N/A",
      new Date(item.confirmed_at).toLocaleString("de-DE"),
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(",")),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `hs_code_export_${new Date().toISOString().split("T")[0]}.csv`,
    );
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
    const blob = new Blob([jsonContent], {
      type: "application/json;charset=utf-8;",
    });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `hs_code_export_${new Date().toISOString().split("T")[0]}.json`,
    );
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  $: totalItemsExport = exportItems.length;
  $: uniqueClustersExport = new Set(exportItems.map((item) => item.cluster_id))
    .size;

  onMount(async () => {
    await fetchDistribution();
    // Fetch initial top level
    await fetchLevel(null, 0);
    await fetchConfirmedItems();
  });

  // refresh when navigating back to the page (SPA) so chart stays up‑to‑date
  afterNavigate(async () => {
    await fetchDistribution();
    await fetchConfirmedItems();
  });

  async function fetchDistribution() {
    loadingDistribution = true;
    try {
      const res = await fetch("http://localhost:8000/analytics/distribution");
      if (res.ok) {
        distributionData = await res.json();
      }
    } catch (e) {
      console.error("Failed to fetch distribution:", e);
    } finally {
      loadingDistribution = false;
    }
  }

  async function fetchAllTariffs() {
    try {
      const res = await fetch("http://localhost:8000/tariffs?limit=1000");
      if (res.ok) {
        allTariffs = await res.json();
      }
    } catch (e) {
      console.error("Failed to fetch tariffs:", e);
    }
  }

  async function loadMaterials(
    tariff_code_id: number | null,
    itemInfo: DistributionItem,
  ) {
    if (tariff_code_id === null) {
      // user clicked the "Unclassified" bar – send them to the
      // assignment/results page so they can handle the remaining data.
      goto("/results");
      return;
    }

    selectedCodeId = tariff_code_id;
    selectedCodeInfo = itemInfo;
    loadingMaterials = true;
    selectedMaterialIds.clear(); // reset selection
    targetTariffCodeId = null;

    try {
      const res = await fetch(
        `http://localhost:8000/materials?tariff_code_id=${tariff_code_id}&limit=500`,
      );
      if (res.ok) {
        materials = await res.json();
      }
    } catch (e) {
      console.error("Failed to fetch materials:", e);
    } finally {
      loadingMaterials = false;
    }
  }

  async function applyBulkUpdate() {
    if (selectedMaterialIds.size === 0 || !targetTariffCodeId) return;

    updating = true;
    try {
      const res = await fetch("http://localhost:8000/materials/bulk-update", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          material_ids: Array.from(selectedMaterialIds),
          new_tariff_code_id: targetTariffCodeId,
        }),
      });

      if (res.ok) {
        // Refresh data
        await fetchDistribution();
        if (selectedCodeId && selectedCodeInfo) {
          await loadMaterials(selectedCodeId, selectedCodeInfo);
        }
        selectedMaterialIds.clear();
        targetTariffCodeId = null;
      } else {
        console.error("Failed to update bulk items");
      }
    } catch (e) {
      console.error("Failed to apply bulk update:", e);
    } finally {
      updating = false;
    }
  }

  function toggleSelectAll(e: Event) {
    const checked = (e.target as HTMLInputElement).checked;
    if (checked) {
      selectedMaterialIds = new Set(materials.map((m) => m.id));
    } else {
      selectedMaterialIds = new Set();
    }
  }

  function toggleMaterial(id: number) {
    const newSet = new Set(selectedMaterialIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    selectedMaterialIds = newSet;
  }

  $: chartData = {
    labels: distributionData.map((d) =>
      d.tariff_code_id === null
        ? "Unclassified"
        : d.goods_code || `Code ${d.tariff_code_id}`,
    ),
    datasets: [
      {
        label: "Material Count",
        data: distributionData.map((d) => d.count),
        backgroundColor: distributionData.map((d) =>
          d.tariff_code_id === null
            ? "rgba(239, 68, 68, 0.7)"
            : "rgba(59, 130, 246, 0.7)",
        ),
        borderColor: distributionData.map((d) =>
          d.tariff_code_id === null
            ? "rgba(239, 68, 68, 1)"
            : "rgba(59, 130, 246, 1)",
        ),
        borderWidth: 1,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    onClick: (e: any, activeEls: any[]) => {
      let index: number | null = null;
      if (activeEls.length > 0) {
        index = activeEls[0].index;
      } else if (chartInstance) {
        // possibly clicked on the label area; compute index from pixel
        const xScale: any = chartInstance.scales["x"];
        if (xScale) {
          const value = xScale.getValueForPixel(e.x);
          if (value !== undefined && value !== null) {
            index = Math.round(value);
          }
        }
      }

      if (index !== null && index >= 0 && index < distributionData.length) {
        const item = distributionData[index];
        if (item.tariff_code_id === null) {
          goto("/results");
        } else {
          loadMaterials(item.tariff_code_id, item);
        }
      }
    },
    plugins: {
      legend: { display: false },
      title: { display: false },
    },
    scales: {
      y: {
        title: { display: true, text: "Number of Materials" },
      },
    },
  };
  let chartInstance: ChartJS | null = null;
  let canvasNode: HTMLCanvasElement;

  function renderChart(node: HTMLCanvasElement) {
    if (chartInstance) {
      chartInstance.destroy();
    }
    chartInstance = new ChartJS(node, {
      type: "bar",
      data: chartData,
      options: chartOptions as any,
    });
  }

  $: if (chartInstance && chartData) {
    chartInstance.data = chartData;
    chartInstance.update();
  }

  onDestroy(() => {
    if (chartInstance) {
      chartInstance.destroy();
    }
  });

  $: filteredTariffs = allTariffs.filter(
    (t) =>
      t.goods_code.includes(tariffSearchQuery) ||
      (t.description &&
        t.description.toLowerCase().includes(tariffSearchQuery.toLowerCase())),
  );
</script>

<div
  class="h-screen flex flex-col bg-gray-50 text-gray-900 font-sans p-6 overflow-auto"
>
  <div class="max-w-7xl mx-auto w-full space-y-6">
    <!-- step navigation -->
    <NavigationHeader currentStep={3} />
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold tracking-tight">
          Tariff Classification Overview
        </h1>
        <p class="text-gray-500 mt-2">
          View the distribution of tariff codes across your materials.
        </p>
      </div>
    </div>

    <!-- Distribution Chart Card -->
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-xl font-semibold mb-6 flex items-center">
        Material Distribution
        <span class="text-sm font-normal text-gray-500 ml-3"
          >(Click a bar to view materials)</span
        >
      </h2>

      {#if loadingDistribution}
        <div class="h-64 flex items-center justify-center">
          <RefreshCw class="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      {:else}
        <div class="h-80 w-full relative">
          <canvas use:renderChart></canvas>
        </div>
      {/if}
    </div>

    <!-- Selected Tariff Details & Materials -->
    {#if selectedCodeId !== null && selectedCodeInfo}
      <div
        class="bg-white rounded-2xl shadow-sm border border-gray-200 flex flex-col min-h-[500px]"
      >
        <div
          class="p-6 border-b border-gray-100 flex flex-col space-y-4 sm:space-y-0 sm:flex-row sm:justify-between sm:items-start"
        >
          <div class="max-w-2xl">
            <div class="flex items-center space-x-3 mb-2">
              <span
                class="inline-flex items-center justify-center px-3 py-1 rounded-full bg-blue-100 text-blue-800 text-sm font-medium"
              >
                {selectedCodeInfo.goods_code}
              </span>
              <span class="text-gray-500 text-sm"
                >{selectedCodeInfo.count} items</span
              >
            </div>
            <h3 class="text-xl font-medium text-gray-900 leading-snug">
              {selectedCodeInfo.description || "No description available"}
            </h3>
          </div>

          <!-- Bulk Actions Banner -->
          {#if selectedMaterialIds.size > 0}
            <div
              class="bg-blue-50 border border-blue-100 rounded-xl p-4 flex flex-col shadow-sm sm:w-80 flex-shrink-0 animate-in fade-in slide-in-from-top-4"
            >
              <div class="text-sm font-medium text-blue-800 mb-3">
                {selectedMaterialIds.size} items selected
              </div>

              <div class="space-y-3">
                <p
                  class="text-[11px] text-blue-700 font-bold uppercase tracking-wider mb-1"
                >
                  Hierarchy Browser
                </p>

                <div
                  class="space-y-2 max-h-64 overflow-y-auto pr-1 custom-scrollbar"
                >
                  {#each hierarchyLevels as level, i}
                    <div class="flex flex-col space-y-1">
                      <label
                        class="text-[9px] uppercase tracking-wider text-gray-400 font-bold"
                      >
                        {i === 0
                          ? "Category"
                          : i === 1
                            ? "Sub-Category"
                            : i === 2
                              ? "Heading"
                              : `Level ${i + 1}`}
                      </label>
                      <select
                        class="w-full py-1.5 px-3 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white shadow-sm"
                        value={level.selected?.id || ""}
                        on:change={(e) => {
                          const id = parseInt(e.currentTarget.value);
                          const item =
                            level.items.find((it) => it.id === id) || null;
                          handleHierarchySelect(i, item);
                        }}
                      >
                        <option value="">Select...</option>
                        {#each level.items as t}
                          <option value={t.id}
                            >{t.goods_code} - {t.description
                              ? t.description.length > 50
                                ? t.description.substring(0, 50) + "..."
                                : t.description
                              : ""}</option
                          >
                        {/each}
                      </select>
                    </div>
                  {/each}

                  {#if loadingHierarchy}
                    <div class="flex items-center justify-center p-2">
                      <RefreshCw class="w-4 h-4 text-blue-400 animate-spin" />
                    </div>
                  {/if}
                </div>

                <div class="pt-2 border-t border-blue-100 mt-2">
                  {#if targetTariffCodeId}
                    <div
                      class="mb-3 p-2 bg-white/60 rounded-lg border border-blue-200 text-[11px] shadow-inner text-blue-900"
                    >
                      <div class="flex items-center space-x-2 mb-1">
                        <span
                          class="px-1.5 py-0.5 bg-blue-600 text-white rounded font-mono font-bold text-[10px]"
                        >
                          {hierarchyLevels[hierarchyLevels.length - 1].selected
                            ?.goods_code}
                        </span>
                        <span class="font-bold">Target Selection</span>
                      </div>
                      <p class="opacity-80 italic line-clamp-2">
                        {hierarchyLevels[hierarchyLevels.length - 1].selected
                          ?.description || "No description"}
                      </p>
                    </div>
                  {/if}
                  <button
                    on:click={applyBulkUpdate}
                    disabled={updating || !targetTariffCodeId}
                    class="w-full flex justify-center items-center py-2.5 px-4 border border-transparent rounded-xl shadow-lg text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98]"
                  >
                    {#if updating}
                      <RefreshCw class="w-4 h-4 animate-spin mr-2" /> Updating...
                    {:else}
                      <CheckCircle class="w-4 h-4 mr-2" /> Reassign Codes
                    {/if}
                  </button>
                </div>
              </div>
            </div>
          {/if}
        </div>

        <!-- Materials Table -->
        <div class="flex-1 overflow-auto">
          {#if loadingMaterials}
            <div class="p-12 flex items-center justify-center text-gray-400">
              Loading materials...
            </div>
          {:else if materials.length === 0}
            <div class="p-12 flex items-center justify-center text-gray-400">
              No materials found for this tariff code.
            </div>
          {:else}
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50 sticky top-0 shadow-sm z-10">
                <tr>
                  <th scope="col" class="px-6 py-3 w-12 pt-4">
                    <input
                      type="checkbox"
                      class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      checked={selectedMaterialIds.size === materials.length &&
                        materials.length > 0}
                      on:change={toggleSelectAll}
                    />
                  </th>
                  <th
                    scope="col"
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >Material ID</th
                  >
                  <th
                    scope="col"
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >Short Text</th
                  >
                  <th
                    scope="col"
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >PO Text</th
                  >
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                {#each materials as mat}
                  <tr
                    class="hover:bg-gray-50 transition-colors {selectedMaterialIds.has(
                      mat.id,
                    )
                      ? 'bg-blue-50/50 hover:bg-blue-50/80'
                      : ''}"
                  >
                    <td class="px-6 py-4 whitespace-nowrap w-12">
                      <input
                        type="checkbox"
                        class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        checked={selectedMaterialIds.has(mat.id)}
                        on:change={() => toggleMaterial(mat.id)}
                      />
                    </td>
                    <td
                      class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                      >{mat.material_number}</td
                    >
                    <td
                      class="px-6 py-4 text-sm text-gray-500 truncate max-w-xs"
                      title={mat.short_text}>{mat.short_text || "-"}</td
                    >
                    <td
                      class="px-6 py-4 text-sm text-gray-500 truncate max-w-xs"
                      title={mat.purchase_order_text}
                      >{mat.purchase_order_text || "-"}</td
                    >
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</div>

<!-- export section (merged) -->
<div class="max-w-7xl mx-auto px-8 py-12">
  <div class="mb-12">
    <h2 class="text-4xl text-[#BB1E38] font-bold mb-2">Export & Abschluss</h2>
    <p class="text-base text-[#6b6b6b]">
      Bestätigte HS-Code-Zuordnungen exportieren
    </p>
  </div>

  {#if errorExport}
    <Alert color="red" class="mb-8">{errorExport}</Alert>
  {/if}

  {#if loadingExport}
    <div class="flex justify-center items-center py-20">
      <div
        class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#BB1E38]"
      ></div>
    </div>
  {:else}
    <!-- Summary Stats -->
    <div class="grid md:grid-cols-3 gap-6 mb-8">
      <div
        class="bg-white rounded-lg shadow-md p-6 border-l-4 border-green-500"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600 font-medium">Bestätigte Artikel</p>
            <p class="text-3xl font-bold text-[#272425] mt-1">
              {totalItemsExport}
            </p>
          </div>
          <CheckCircle class="h-12 w-12 text-green-500 opacity-80" />
        </div>
      </div>

      <div class="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-500">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600 font-medium">Cluster</p>
            <p class="text-3xl font-bold text-[#272425] mt-1">
              {uniqueClustersExport}
            </p>
          </div>
          <div
            class="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center"
          >
            <span class="text-2xl font-bold text-blue-600">C</span>
          </div>
        </div>
      </div>

      <div
        class="bg-white rounded-lg shadow-md p-6 border-l-4 border-[#BB1E38]"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600 font-medium">Bereit zum Export</p>
            <p class="text-3xl font-bold text-[#272425] mt-1">✓</p>
          </div>
          <span class="h-12 w-12 text-[#BB1E38] opacity-80">
            <!-- icon placeholder -->
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              class="h-12 w-12"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 17v-6a2 2 0 012-2h2a2 2 0 012 2v6m-4 0v4m0-4h4m-4 0H5"
              />
            </svg>
          </span>
        </div>
      </div>
    </div>

    <!-- Export Options -->
    <div class="bg-white rounded-xl shadow-lg p-8 mb-8">
      <h3 class="text-2xl font-semibold text-[#272425] mb-6">
        Export-Optionen
      </h3>
      {#if totalItemsExport === 0}
        <div class="text-center py-12">
          <span class="mx-auto h-16 w-16 text-gray-300 mb-4 block">📄</span>
          <p class="text-gray-500 text-lg mb-2">
            Keine bestätigten Einträge vorhanden
          </p>
          <p class="text-gray-400 text-sm mb-6">
            Bitte bestätigen Sie zunächst einige Zuordnungen auf der
            Ergebnisseite.
          </p>
        </div>
      {:else}
        <div class="grid md:grid-cols-2 gap-6">
          <button
            on:click={exportToCSV}
            class="group relative overflow-hidden border-2 border-gray-200 rounded-lg p-8 hover:border-[#BB1E38] hover:shadow-lg transition-all"
          >
            <div class="relative z-10">
              <div class="flex items-center justify-between mb-4">
                <span class="h-12 w-12 text-green-600">📄</span>
                <span
                  class="h-8 w-8 text-gray-400 group-hover:text-[#BB1E38] transition-colors"
                  >⬇️</span
                >
              </div>
              <p class="text-lg font-semibold">CSV herunterladen</p>
              <p class="text-sm text-gray-500 mt-1">Komma-separierte Werte</p>
            </div>
          </button>

          <button
            on:click={exportToJSON}
            class="group relative overflow-hidden border-2 border-gray-200 rounded-lg p-8 hover:border-[#BB1E38] hover:shadow-lg transition-all"
          >
            <div class="relative z-10">
              <div class="flex items-center justify-between mb-4">
                <span class="h-12 w-12 text-indigo-600">🗂️</span>
                <span
                  class="h-8 w-8 text-gray-400 group-hover:text-[#BB1E38] transition-colors"
                  >⬇️</span
                >
              </div>
              <p class="text-lg font-semibold">JSON herunterladen</p>
              <p class="text-sm text-gray-500 mt-1">Strukturierte Daten</p>
            </div>
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>
