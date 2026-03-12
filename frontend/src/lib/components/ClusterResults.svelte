<script lang="ts">
  import {
    ChevronDown,
    ChevronRight,
    CheckCircle,
    AlertTriangle,
    HelpCircle,
    RefreshCw,
  } from "lucide-svelte";

  import { createEventDispatcher } from "svelte";

  export let clusters: any[] = [];
  export let loading: boolean = false;

  const dispatch = createEventDispatcher();

  const API_URL = "http://localhost:8000";

  let expandedClusters: Set<string> = new Set();

  // Track user selections and confirmations for each item
  // Format: { "clusterId-itemId": "tariff_code" }
  let itemSelections: Record<string, string> = {};

  // Format: Set of "clusterId-itemId" for confirmed items
  let confirmedItems: Set<string> = new Set();

  // Track confidence scores for selections
  let itemConfidenceScores: Record<string, number> = {};

  // Track cluster-level confirmations
  let confirmedClusters: Set<string> = new Set();
  let confirmingClusters: Set<string> = new Set();

  // Track which tariff code is actively selected for each cluster (before confirmation)
  let clusterActiveSelections: Record<string, string> = {};

  // IMMEDIATE visual feedback - gets set instantly on button click
  let visuallyConfirmedClusters: Set<string> = new Set();

  function toggleCluster(clusterId: string) {
    if (expandedClusters.has(clusterId)) {
      expandedClusters.delete(clusterId);
    } else {
      expandedClusters.add(clusterId);
    }
    expandedClusters = expandedClusters; // Trigger reactivity
  }

  function selectTariffForItem(
    clusterId: string,
    itemId: string,
    tariffCode: string,
    confidenceScore: number,
  ) {
    const key = `${clusterId}-${itemId}`;
    itemSelections[key] = tariffCode;
    itemConfidenceScores[key] = confidenceScore;
    itemSelections = itemSelections; // Trigger reactivity
  }

  async function confirmItem(clusterId: string, itemId: string) {
    const key = `${clusterId}-${itemId}`;
    const selectedTariff = itemSelections[key];

    if (!selectedTariff) {
      console.error("No tariff selected for item", itemId);
      return;
    }

    // note: dispatch progress after successful confirmation below

    try {
      const response = await fetch(`${API_URL}/confirmations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          material_number: itemId,
          cluster_id: clusterId,
          assigned_tariff_code: selectedTariff,
          confidence_score: itemConfidenceScores[key] || null,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to confirm assignment");
      }

      const result = await response.json();
      console.log(
        `Confirmed: Material ${itemId} with HS code ${selectedTariff}`,
        result,
      );

      // Add to confirmed items
      confirmedItems.add(key);
      confirmedItems = new Set(confirmedItems); // Trigger reactivity by creating new Set

      // notify parent that something has been confirmed
      dispatch("progress", { confirmedItems: confirmedItems.size });
    } catch (error) {
      console.error("Error confirming item:", error);
      alert(
        "Fehler beim Speichern der Bestätigung. Bitte versuchen Sie es erneut.",
      );
    }
  }

  async function confirmWholeCluster(
    cluster: any,
    tariffCode?: string,
    confidenceScore?: number,
  ) {
    // If a manual tariffCode was provided we skip the usual suggestion check
    if (!tariffCode) {
      if (
        !cluster.tariff_suggestions ||
        cluster.tariff_suggestions.length === 0
      ) {
        alert("Keine Zollnummern-Vorschläge für diesen Cluster vorhanden.");
        return;
      }
    }

    // Determine which suggestion to use (manual override or top suggestion)
    let suggestion: any;
    if (tariffCode) {
      // build a lightweight suggestion-like object from manual input
      suggestion = {
        tariff_code: tariffCode,
        confidence_score: confidenceScore ?? null,
      };
    } else {
      suggestion = cluster.tariff_suggestions[0];
    }

    const clusterId = cluster.cluster_id;

    console.log(
      `🔄 Starting confirmation for cluster ${clusterId} with tariff ${suggestion.tariff_code}`,
    );

    // ⚡ SET VISUAL STATE IMMEDIATELY - BEFORE API CALL
    visuallyConfirmedClusters.add(clusterId);
    visuallyConfirmedClusters = new Set(visuallyConfirmedClusters);
    console.log(
      `⚡ INSTANT VISUAL UPDATE! Cluster ${clusterId} added to visuallyConfirmedClusters`,
      Array.from(visuallyConfirmedClusters),
    );

    // Mark this tariff as actively selected for visual feedback
    clusterActiveSelections[clusterId] = suggestion.tariff_code;
    clusterActiveSelections = { ...clusterActiveSelections };

    confirmingClusters.add(clusterId);
    confirmingClusters = new Set(confirmingClusters);

    try {
      // Confirm all items in the cluster with the selected suggestion
      const confirmPromises = cluster.items.map(async (item: any) => {
        const key = `${clusterId}-${item.item_id}`;

        // Set the selection for this item
        itemSelections[key] = suggestion.tariff_code;
        itemConfidenceScores[key] = suggestion.confidence_score;

        // Confirm via API
        const response = await fetch(`${API_URL}/confirmations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            material_number: item.item_id,
            cluster_id: clusterId,
            assigned_tariff_code: suggestion.tariff_code,
            confidence_score: suggestion.confidence_score,
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to confirm ${item.item_id}`);
        }

        // Add to confirmed items
        confirmedItems.add(key);

        // dispatch progress event for each item confirmation
        dispatch("progress", { confirmedItems: confirmedItems.size });

        return response.json();
      });

      await Promise.all(confirmPromises);

      // Mark cluster as confirmed - FORCE reactivity update
      confirmedClusters.add(clusterId);
      confirmedClusters = new Set(confirmedClusters); // Force Svelte reactivity
      confirmedItems = new Set(confirmedItems);
      itemSelections = { ...itemSelections };

      // dispatch progress event so parent can update nav state
      dispatch("progress", { confirmedClusters: confirmedClusters.size });

      // Auto-collapse the cluster after confirmation
      expandedClusters.delete(clusterId);
      expandedClusters = new Set(expandedClusters); // Force Svelte reactivity

      console.log(
        `✅ Confirmed entire cluster ${clusterId} with ${cluster.items.length} items using HS code ${suggestion.tariff_code}`,
      );
      console.log("Confirmed clusters:", Array.from(confirmedClusters));
    } catch (error) {
      console.error("Error confirming cluster:", error);
      alert(
        "Fehler beim Bestätigen des Clusters. Bitte versuchen Sie es erneut.",
      );

      // Remove from visual state on error
      visuallyConfirmedClusters.delete(clusterId);
      visuallyConfirmedClusters = new Set(visuallyConfirmedClusters);

      // Remove active selection on error
      delete clusterActiveSelections[clusterId];
      clusterActiveSelections = clusterActiveSelections;
    } finally {
      confirmingClusters.delete(clusterId);
      confirmingClusters = confirmingClusters;
    }
  }

  function isClusterConfirmed(clusterId: string): boolean {
    // immediate visual or backend confirmation wins
    if (
      visuallyConfirmedClusters.has(clusterId) ||
      confirmedClusters.has(clusterId)
    ) {
      console.log(
        `✅ isClusterConfirmed(${clusterId}) = TRUE (visual/backend)`,
      );
      return true;
    }

    // also consider a cluster fully confirmed if every item within it has
    // been individually confirmed. this allows removing a cluster after the
    // last item is marked, not only when the user uses the "confirm whole
    // cluster" button.
    const cluster = clusters.find((c) => c.cluster_id === clusterId);
    if (cluster && cluster.items && cluster.items.length > 0) {
      const allItemsConfirmed = cluster.items.every((item: any) =>
        confirmedItems.has(`${clusterId}-${item.item_id}`),
      );
      if (allItemsConfirmed) {
        console.log(
          `✅ isClusterConfirmed(${clusterId}) = TRUE (all items confirmed)`,
        );
        return true;
      }
    }

    return false;
  }

  function isClusterConfirming(clusterId: string): boolean {
    return confirmingClusters.has(clusterId);
  }

  function isItemConfirmed(clusterId: string, itemId: string): boolean {
    return confirmedItems.has(`${clusterId}-${itemId}`);
  }

  function getSelectedTariff(clusterId: string, itemId: string): string | null {
    return itemSelections[`${clusterId}-${itemId}`] || null;
  }

  function getConfidenceColor(score: number): string {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.5) return "text-yellow-600";
    return "text-red-600";
  }

  function getConfidenceBadge(score: number): string {
    if (score >= 0.8) return "bg-green-100 text-green-800";
    if (score >= 0.5) return "bg-yellow-100 text-yellow-800";
    return "bg-red-100 text-red-800";
  }

  function getStatusBadge(status: string): { class: string; label: string } {
    switch (status) {
      case "completed":
        return { class: "bg-green-100 text-green-800", label: "Analysiert" };
      case "processing":
        return { class: "bg-blue-100 text-blue-800", label: "Verarbeitung..." };
      case "error":
        return { class: "bg-red-100 text-red-800", label: "Fehler" };
      default:
        return { class: "bg-gray-100 text-gray-800", label: "Ausstehend" };
    }
  }

  // Get top N tariff suggestions
  function getTopSuggestions(suggestions: any[], count: number) {
    return suggestions ? suggestions.slice(0, count) : [];
  }

  /**
   * --- Custom assignment support (hierarchical picker) ---
   * We reuse the same hierarchy approach from overview/+page.svelte but
   * keep state per-cluster so users can assign any code to a cluster.
   */
  interface TariffCode {
    id: number;
    goods_code: string;
    description: string | null;
  }

  // track which clusters currently have the custom picker expanded
  let clusterSelectingCustom: Set<string> = new Set();

  // per-cluster hierarchy state
  let clusterHierarchy: Record<
    string,
    {
      levels: { items: TariffCode[]; selected: TariffCode | null }[];
      loading: boolean;
      targetCode: TariffCode | null;
    }
  > = {};

  async function fetchClusterLevel(
    clusterId: string,
    parentId: number | null,
    levelIndex: number,
  ) {
    const state = clusterHierarchy[clusterId];
    if (!state) return;
    state.loading = true;
    try {
      const url = parentId
        ? `http://localhost:8000/tariffs/hierarchy?parent_id=${parentId}`
        : "http://localhost:8000/tariffs/hierarchy";
      const res = await fetch(url);
      if (res.ok) {
        const items = await res.json();
        state.levels[levelIndex].items = items;
        // trigger reactivity
        clusterHierarchy = { ...clusterHierarchy };
      }
    } catch (e) {
      console.error("Failed to fetch hierarchy for cluster", clusterId, e);
    } finally {
      state.loading = false;
    }
  }

  async function handleClusterHierarchySelect(
    clusterId: string,
    levelIndex: number,
    item: TariffCode | null,
  ) {
    const state = clusterHierarchy[clusterId];
    if (!state) return;

    state.levels = state.levels.slice(0, levelIndex + 1);
    state.levels[levelIndex].selected = item;

    if (item) {
      state.targetCode = item;
      // prepare next level
      state.levels.push({ items: [], selected: null });
      await fetchClusterLevel(clusterId, item.id, levelIndex + 1);
      if (state.levels[levelIndex + 1].items.length === 0) {
        state.levels = state.levels.slice(0, levelIndex + 1);
      }
    } else {
      state.targetCode =
        levelIndex > 0 ? state.levels[levelIndex - 1].selected : null;
    }
    // reassign so Svelte updates
    clusterHierarchy = { ...clusterHierarchy };
  }

  function startCustomAssign(clusterId: string) {
    clusterSelectingCustom.add(clusterId);
    clusterSelectingCustom = new Set(clusterSelectingCustom);
    clusterHierarchy[clusterId] = {
      levels: [{ items: [], selected: null }],
      loading: false,
      targetCode: null,
    };
    // fetch first level
    fetchClusterLevel(clusterId, null, 0);
  }

  function cancelCustomAssign(clusterId: string) {
    clusterSelectingCustom.delete(clusterId);
    clusterSelectingCustom = new Set(clusterSelectingCustom);
    delete clusterHierarchy[clusterId];
    clusterHierarchy = { ...clusterHierarchy };
  }

  // Calculate confirmation progress
  $: confirmedCount = confirmedClusters.size;
  $: visuallyConfirmedCount = visuallyConfirmedClusters.size; // Force Svelte to track visual confirmations
  $: totalClusters = clusters.length;
  // use visual count for progress so UI moves immediately when a cluster is marked
  $: confirmationProgress =
    totalClusters > 0 ? (visuallyConfirmedCount / totalClusters) * 100 : 0;

  // Create reactive map of confirmed statuses - this forces Svelte to re-render when confirmation state changes
  // we include a dummy reference to confirmedItems.size so that the map updates when
  // individual item confirmations modify the set
  $: clusterConfirmedMap = (() => {
    // add dummy references so that this reactive statement re‑runs when any of the
    // confirmation-related sets change
    const _watchItems = confirmedItems.size; // eslint-disable-line no-unused-vars
    const _watchVisual = visuallyConfirmedClusters.size; // eslint-disable-line no-unused-vars
    const _watchClusters = confirmedClusters.size; // eslint-disable-line no-unused-vars
    return clusters.reduce(
      (map, c) => {
        map[c.cluster_id] = isClusterConfirmed(c.cluster_id);
        return map;
      },
      {} as Record<string, boolean>,
    );
  })();

  // derive the list of clusters that are still unconfirmed
  $: unconfirmedClusters = clusters.filter(
    (c) => !clusterConfirmedMap[c.cluster_id],
  );
</script>

<div
  class="border border-gray-200 bg-white shadow-sm rounded-lg overflow-hidden"
>
  <div class="p-6 border-b border-gray-200 bg-gray-50">
    <!-- Progress Indicator -->
    {#if totalClusters > 0}
      <div class="mt-4 bg-white rounded-lg border border-gray-200 p-4">
        <span class="text-sm font-medium text-[#272425]"
          >Bestätigungsfortschritt</span
        >
        <span
          class="text-sm font-semibold {visuallyConfirmedCount === totalClusters
            ? 'text-green-700'
            : 'text-[#BB1E38]'}"
        >
          {visuallyConfirmedCount} / {totalClusters} Cluster bestätigt
        </span>
        <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            class="h-3 rounded-full transition-all duration-500 ease-out {visuallyConfirmedCount ===
            totalClusters
              ? 'bg-green-600'
              : 'bg-[#BB1E38]'}"
            style="width: {confirmationProgress}%"
          ></div>
        </div>
        {#if visuallyConfirmedCount === totalClusters && totalClusters > 0}
          <p
            class="mt-2 text-sm text-green-700 font-medium flex items-center gap-2"
          >
            <CheckCircle class="h-4 w-4" />
            Alle Cluster wurden bestätigt! Sie können nun zum Export fortfahren.
          </p>
        {:else if visuallyConfirmedCount > 0}
          <p class="mt-2 text-sm text-[#6b6b6b]">
            Noch {totalClusters - visuallyConfirmedCount} Cluster verbleibend
          </p>
        {/if}
      </div>
    {/if}
  </div>

  {#if loading}
    <div class="p-12 text-center">
      <div
        class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#BB1E38]"
      ></div>
      <p class="mt-4 text-[#6b6b6b]">Lade Cluster-Daten...</p>
    </div>
  {:else if unconfirmedClusters.length === 0}
    <div class="p-12 text-center text-[#6b6b6b]">
      <AlertTriangle class="mx-auto h-12 w-12 mb-4 text-gray-400" />
      <p>Keine unbestätigten Cluster gefunden.</p>
    </div>
  {:else}
    <div class="divide-y divide-gray-200">
      {#each unconfirmedClusters as cluster (cluster.cluster_id)}
        {@const isConfirmed = clusterConfirmedMap[cluster.cluster_id] || false}
        {@const confirmedTariff =
          isConfirmed && clusterActiveSelections[cluster.cluster_id]
            ? clusterActiveSelections[cluster.cluster_id]
            : cluster.tariff_suggestions?.[0]?.tariff_code}
        {@const confirmedConfidence = cluster.tariff_suggestions?.find(
          (s) => s.tariff_code === confirmedTariff,
        )?.confidence_score}

        <div
          class="transition-all duration-500 {isConfirmed
            ? 'bg-gradient-to-r from-green-100 to-green-50 border-l-8 border-green-600 shadow-lg scale-[0.99]'
            : 'hover:bg-gray-50 border-l-4 border-transparent scale-100'}"
        >
          <!-- Cluster Header -->
          <div class="px-6 py-5 flex items-center justify-between">
            <button
              on:click={() => toggleCluster(cluster.cluster_id)}
              class="flex items-center gap-4 flex-1 text-left focus:outline-none"
            >
              <div class="flex-shrink-0">
                {#if expandedClusters.has(cluster.cluster_id)}
                  <ChevronDown
                    class="h-5 w-5 {isConfirmed
                      ? 'text-green-700'
                      : 'text-gray-500'}"
                  />
                {:else}
                  <ChevronRight
                    class="h-5 w-5 {isConfirmed
                      ? 'text-green-700'
                      : 'text-gray-500'}"
                  />
                {/if}
              </div>

              <div class="flex-1">
                {#if isConfirmed}
                  <!-- Confirmed Cluster Header - SUPER OBVIOUS -->
                  <div class="bg-green-600 text-white rounded-lg p-3 shadow-md">
                    <div class="flex items-center gap-3 mb-2">
                      <CheckCircle
                        class="h-7 w-7 flex-shrink-0 animate-pulse"
                      />
                      <h3 class="text-xl font-bold">{cluster.cluster_name}</h3>
                      <span
                        class="px-3 py-1 rounded-full text-xs font-bold bg-white text-green-700"
                      >
                        {cluster.item_count} ARTIKEL BESTÄTIGT
                      </span>
                    </div>
                    <div class="flex items-center gap-2 text-sm ml-10">
                      <span class="font-semibold">HS-Code:</span>
                      <span
                        class="font-mono font-bold text-lg bg-white text-green-700 px-3 py-1 rounded"
                      >
                        {confirmedTariff}
                      </span>
                      {#if confirmedConfidence}
                        <span
                          class="px-2 py-1 rounded text-xs font-bold bg-green-500 text-white"
                        >
                          {Math.round(confirmedConfidence * 100)}% Konfidenz
                        </span>
                      {/if}
                    </div>
                  </div>
                {:else}
                  <!-- Unconfirmed Cluster Header -->
                  <div class="flex items-center gap-3">
                    <h3 class="text-lg font-semibold text-[#272425]">
                      {cluster.cluster_name}
                    </h3>
                    <span
                      class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                    >
                      {cluster.item_count}
                      {cluster.item_count === 1 ? "Artikel" : "Artikel"}
                    </span>
                    <span
                      class="px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusBadge(
                        cluster.status,
                      ).class}"
                    >
                      {getStatusBadge(cluster.status).label}
                    </span>
                  </div>

                  {#if cluster.tariff_suggestions && cluster.tariff_suggestions.length > 0}
                    <div class="mt-2 flex items-center gap-2 text-sm">
                      <span class="text-[#6b6b6b]"
                        >Vorgeschlagener HS-Code:</span
                      >
                      <span class="font-mono font-semibold text-[#BB1E38]">
                        {cluster.tariff_suggestions[0].tariff_code}
                      </span>
                      <span
                        class="px-2 py-0.5 rounded text-xs font-medium {getConfidenceBadge(
                          cluster.tariff_suggestions[0].confidence_score,
                        )}"
                      >
                        {Math.round(
                          cluster.tariff_suggestions[0].confidence_score * 100,
                        )}% Konfidenz
                      </span>
                    </div>
                  {/if}
                {/if}
              </div>
            </button>

            <!-- Cluster-wide Confirm Button (Collapsed View) -->
            {#if isConfirmed}
              <!-- Show COMPLETED badge instead of button -->
              <div
                class="ml-4 inline-flex items-center gap-3 px-6 py-3 bg-green-600 text-white rounded-lg shadow-lg"
              >
                <CheckCircle class="h-6 w-6 animate-pulse" />
                <div class="text-left">
                  <div class="font-bold text-sm">BESTÄTIGT</div>
                  <div class="text-xs opacity-90">
                    {cluster.item_count} Artikel gespeichert
                  </div>
                </div>
              </div>
            {:else if cluster.tariff_suggestions && cluster.tariff_suggestions.length > 0}
              <button
                on:click={(e) => {
                  e.stopPropagation();
                  confirmWholeCluster(cluster);
                }}
                disabled={isClusterConfirming(cluster.cluster_id)}
                class="ml-4 inline-flex items-center justify-center px-5 py-3 text-sm font-bold rounded-lg
                       bg-[#BB1E38] hover:bg-[#9a1830] hover:shadow-xl text-white
                       disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105"
              >
                {#if isClusterConfirming(cluster.cluster_id)}
                  <div
                    class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"
                  ></div>
                  Bestätige...
                {:else}
                  <CheckCircle class="h-4 w-4 mr-2" />
                  Alle Artikel mit Top-Vorschlag bestätigen
                {/if}
              </button>
            {/if}
          </div>

          <!-- Expanded Content -->
          {#if expandedClusters.has(cluster.cluster_id)}
            <div
              class="px-6 pb-6 {isConfirmed
                ? 'bg-green-50/50'
                : 'bg-gray-50/50'}"
            >
              {#if isConfirmed}
                <!-- Confirmed Cluster Info Banner -->
                <div
                  class="mb-4 bg-green-100 border border-green-300 rounded-lg p-4"
                >
                  <div class="flex items-center gap-3">
                    <CheckCircle class="h-6 w-6 text-green-700 flex-shrink-0" />
                    <div>
                      <p class="font-semibold text-green-900">
                        Cluster vollständig bestätigt
                      </p>
                      <p class="text-sm text-green-800 mt-1">
                        Alle {cluster.item_count} Artikel wurden mit HS-Code
                        <span class="font-mono font-bold"
                          >{confirmedTariff}</span
                        > bestätigt. Die Bestätigungen wurden gespeichert und können
                        beim Export verwendet werden.
                      </p>
                    </div>
                  </div>
                </div>
              {/if}

              <!-- Tariff Suggestions -->
              {#if cluster.tariff_suggestions && cluster.tariff_suggestions.length > 0}
                <div
                  class="mb-6 bg-white rounded-lg border border-gray-200 p-4"
                >
                  <div class="mb-3">
                    <h4
                      class="font-semibold text-[#272425] flex items-center gap-2"
                    >
                      <CheckCircle class="h-5 w-5 text-green-600" />
                      LLM-Vorschläge für Zollnummern (Top 3)
                    </h4>
                  </div>

                  <div class="space-y-3">
                    {#each getTopSuggestions(cluster.tariff_suggestions, 3) as suggestion, idx}
                      <div
                        class="border-l-4 {idx === 0
                          ? 'border-green-500'
                          : 'border-gray-300'} pl-4 py-2"
                      >
                        <div class="flex items-start justify-between gap-4">
                          <div class="flex-1">
                            <div class="flex items-center gap-3 mb-1">
                              <span
                                class="font-mono text-lg font-bold text-[#272425]"
                              >
                                {suggestion.tariff_code}
                              </span>
                              <span
                                class="px-2 py-0.5 rounded text-xs font-medium {getConfidenceBadge(
                                  suggestion.confidence_score,
                                )}"
                              >
                                {Math.round(suggestion.confidence_score * 100)}%
                              </span>
                              {#if idx === 0}
                                <span
                                  class="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800"
                                >
                                  Empfohlen
                                </span>
                              {/if}
                            </div>
                            {#if suggestion.section_info}
                              <p class="text-xs text-[#6b6b6b] mb-2">
                                {suggestion.section_info}
                              </p>
                            {/if}
                            <p class="text-sm text-[#272425]">
                              {suggestion.reasoning}
                            </p>
                          </div>

                          <!-- Select Button for Each Recommendation -->
                          {#if !isConfirmed}
                            {@const isThisSelected =
                              clusterActiveSelections[cluster.cluster_id] ===
                              suggestion.tariff_code}
                            <button
                              on:click={() =>
                                confirmWholeCluster(
                                  cluster,
                                  suggestion.tariff_code,
                                  suggestion.confidence_score,
                                )}
                              disabled={isClusterConfirming(cluster.cluster_id)}
                              class="flex-shrink-0 inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md
                                     transition-all duration-200
                                     {isClusterConfirming(cluster.cluster_id)
                                ? 'bg-gray-400 cursor-wait'
                                : isThisSelected
                                  ? 'bg-green-600 hover:bg-green-700 text-white'
                                  : idx === 0
                                    ? 'bg-[#BB1E38] hover:bg-[#9a1830] text-white'
                                    : 'bg-gray-600 hover:bg-gray-700 text-white'}
                                     disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {#if isClusterConfirming(cluster.cluster_id)}
                                <div
                                  class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"
                                ></div>
                                Bestätige...
                              {:else if isThisSelected}
                                <CheckCircle class="h-4 w-4 mr-1" />
                                Selected
                              {:else}
                                Select
                              {/if}
                            </button>
                          {:else}
                            <div
                              class="flex-shrink-0 inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md bg-green-100 text-green-800 border border-green-300"
                            >
                              <CheckCircle class="h-4 w-4 mr-1" />
                              Bestätigt
                            </div>
                          {/if}
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- custom assignment section -->
              {#if !isConfirmed}
                <div class="mb-6 px-4">
                  <button
                    class="text-sm text-[#BB1E38] underline hover:text-[#9a1830]"
                    on:click={() => {
                      if (clusterSelectingCustom.has(cluster.cluster_id)) {
                        cancelCustomAssign(cluster.cluster_id);
                      } else {
                        startCustomAssign(cluster.cluster_id);
                      }
                    }}
                  >
                    {clusterSelectingCustom.has(cluster.cluster_id)
                      ? "Abbrechen"
                      : "Andere Zollnummer zuweisen"}
                  </button>

                  {#if clusterSelectingCustom.has(cluster.cluster_id)}
                    <div
                      class="mt-4 bg-gray-50 p-4 rounded-lg border border-gray-200"
                    >
                      <p class="text-sm font-medium mb-2">
                        Wähle eine Zollnummer aus der Hierarchie
                      </p>
                      <div class="space-y-3">
                        {#each clusterHierarchy[cluster.cluster_id].levels as level, li}
                          <div class="flex flex-col space-y-1">
                            <label
                              class="text-[9px] uppercase tracking-wider text-gray-400 font-bold"
                            >
                              {li === 0
                                ? "Kategorie"
                                : li === 1
                                  ? "Unterkategorie"
                                  : li === 2
                                    ? "Head"
                                    : `Ebene ${li + 1}`}
                            </label>
                            <select
                              class="w-full py-1.5 px-3 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white shadow-sm"
                              value={level.selected?.id || ""}
                              on:change={(e) => {
                                const id = parseInt(e.currentTarget.value);
                                const item =
                                  level.items.find((it) => it.id === id) ||
                                  null;
                                handleClusterHierarchySelect(
                                  cluster.cluster_id,
                                  li,
                                  item,
                                );
                              }}
                            >
                              <option value="">Select...</option>
                              {#each level.items as t}
                                <option value={t.id}>
                                  {t.goods_code} - {t.description
                                    ? t.description.length > 50
                                      ? t.description.substring(0, 50) + "..."
                                      : t.description
                                    : ""}
                                </option>
                              {/each}
                            </select>
                          </div>
                        {/each}

                        {#if clusterHierarchy[cluster.cluster_id].loading}
                          <div class="flex items-center justify-center p-2">
                            <RefreshCw
                              class="w-4 h-4 text-blue-400 animate-spin"
                            />
                          </div>
                        {/if}
                      </div>

                      <div class="mt-4 flex items-center gap-2">
                        <button
                          class="px-4 py-2 bg-[#BB1E38] text-white rounded-lg text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                          disabled={!clusterHierarchy[cluster.cluster_id]
                            .targetCode}
                          on:click={async () => {
                            const codeObj =
                              clusterHierarchy[cluster.cluster_id].targetCode;
                            if (codeObj) {
                              await confirmWholeCluster(
                                cluster,
                                codeObj.goods_code,
                                null,
                              );
                              cancelCustomAssign(cluster.cluster_id);
                            }
                          }}
                        >
                          Bestätige benutzerdefinierte Zollnummer
                        </button>
                      </div>
                    </div>
                  {/if}
                </div>
              {/if}

              <!-- Items in Cluster -->
              <div
                class="bg-white rounded-lg border border-gray-200 overflow-hidden"
              >
                <div class="px-4 py-3 bg-gray-100 border-b border-gray-200">
                  <h4 class="font-semibold text-[#272425]">
                    Artikel in diesem Cluster
                  </h4>
                </div>

                <div class="overflow-x-auto">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th
                          class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32"
                        >
                          Material-Nr.
                        </th>
                        <th
                          class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-48"
                        >
                          Beschreibung
                        </th>
                        <th
                          class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-64"
                        >
                          Zollnummer (Top 2)
                        </th>
                        <th
                          class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          Details (Einkaufsbestelltext)
                        </th>
                        <th
                          class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-32"
                        >
                          Bestätigen
                        </th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      {#each cluster.items as item}
                        {@const top2Suggestions = getTopSuggestions(
                          cluster.tariff_suggestions || [],
                          2,
                        )}
                        {@const itemKey = `${cluster.cluster_id}-${item.item_id}`}
                        {@const isConfirmed = isItemConfirmed(
                          cluster.cluster_id,
                          item.item_id,
                        )}
                        {@const selectedTariff = getSelectedTariff(
                          cluster.cluster_id,
                          item.item_id,
                        )}

                        <tr
                          class="hover:bg-gray-50 {isConfirmed
                            ? 'bg-green-50'
                            : ''}"
                        >
                          <td
                            class="px-4 py-3 whitespace-nowrap text-sm font-medium text-[#272425]"
                          >
                            {item.item_id}
                            {#if isConfirmed}
                              <CheckCircle
                                class="inline h-4 w-4 text-green-600 ml-1"
                              />
                            {/if}
                          </td>
                          <td class="px-4 py-3 text-sm text-[#6b6b6b]">
                            {item.raw_description}
                          </td>
                          <td class="px-4 py-3 text-sm">
                            {#if top2Suggestions.length > 0}
                              <div class="space-y-2">
                                {#each top2Suggestions as suggestion, idx}
                                  {@const isSelected =
                                    selectedTariff === suggestion.tariff_code}
                                  <label
                                    class="flex items-start gap-2 {isConfirmed
                                      ? 'cursor-not-allowed opacity-75'
                                      : 'cursor-pointer hover:bg-gray-100'} p-2 rounded transition-all {isSelected
                                      ? 'bg-blue-50 border-2 border-blue-400 shadow-sm'
                                      : 'border-2 border-transparent'}"
                                  >
                                    <input
                                      type="radio"
                                      name="tariff-{itemKey}"
                                      value={suggestion.tariff_code}
                                      disabled={isConfirmed}
                                      checked={isSelected}
                                      on:change={() =>
                                        selectTariffForItem(
                                          cluster.cluster_id,
                                          item.item_id,
                                          suggestion.tariff_code,
                                          suggestion.confidence_score,
                                        )}
                                      class="mt-1 h-4 w-4 text-[#BB1E38] focus:ring-[#BB1E38] disabled:opacity-50 cursor-pointer"
                                    />
                                    <div class="flex-1">
                                      <div
                                        class="flex items-center gap-2 flex-wrap"
                                      >
                                        <span
                                          class="font-mono font-semibold text-[#272425]"
                                        >
                                          {suggestion.tariff_code}
                                        </span>
                                        <span
                                          class="px-1.5 py-0.5 rounded text-xs {getConfidenceBadge(
                                            suggestion.confidence_score,
                                          )}"
                                        >
                                          {Math.round(
                                            suggestion.confidence_score * 100,
                                          )}%
                                        </span>
                                        {#if idx === 0}
                                          <span
                                            class="px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-800"
                                          >
                                            Empfohlen
                                          </span>
                                        {/if}
                                        {#if isSelected && !isConfirmed}
                                          <span
                                            class="px-1.5 py-0.5 rounded text-xs bg-blue-600 text-white flex items-center gap-1 animate-pulse"
                                          >
                                            <CheckCircle class="h-3 w-3" />
                                            Selected
                                          </span>
                                        {/if}
                                      </div>
                                    </div>
                                  </label>
                                {/each}
                              </div>
                            {:else}
                              <span class="text-gray-400 text-xs"
                                >Keine Vorschläge</span
                              >
                            {/if}
                          </td>
                          <td class="px-4 py-3 text-sm text-[#6b6b6b] max-w-xs">
                            <div
                              class="whitespace-pre-wrap text-xs leading-relaxed"
                            >
                              {item.purchase_order_text ||
                                "Keine Details verfügbar"}
                            </div>
                          </td>
                          <td class="px-4 py-3 text-center">
                            {#if isConfirmed}
                              <div
                                class="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium rounded-md bg-green-600 text-white"
                              >
                                <CheckCircle class="h-4 w-4 mr-1" />
                                Confirmed
                              </div>
                            {:else if selectedTariff}
                              <button
                                on:click={() =>
                                  confirmItem(cluster.cluster_id, item.item_id)}
                                class="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium rounded-md
                                       transition-all duration-200 bg-[#BB1E38] hover:bg-[#9a1830] text-white hover:scale-105 active:scale-95"
                              >
                                Confirm Selection
                              </button>
                            {:else}
                              <button
                                disabled
                                class="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium rounded-md
                                       bg-gray-300 text-gray-500 cursor-not-allowed"
                              >
                                Select Tariff First
                              </button>
                            {/if}
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
