<script lang="ts">
  import { ChevronDown, ChevronRight, CheckCircle, AlertTriangle, HelpCircle } from "lucide-svelte";

  export let clusters: any[] = [];
  export let loading: boolean = false;

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

  function toggleCluster(clusterId: string) {
    if (expandedClusters.has(clusterId)) {
      expandedClusters.delete(clusterId);
    } else {
      expandedClusters.add(clusterId);
    }
    expandedClusters = expandedClusters; // Trigger reactivity
  }

  function selectTariffForItem(clusterId: string, itemId: string, tariffCode: string, confidenceScore: number) {
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

    try {
      const response = await fetch(`${API_URL}/confirmations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          material_number: itemId,
          cluster_id: clusterId,
          assigned_tariff_code: selectedTariff,
          confidence_score: itemConfidenceScores[key] || null
        })
      });

      if (!response.ok) {
        throw new Error("Failed to confirm assignment");
      }

      const result = await response.json();
      console.log(`Confirmed: Material ${itemId} with HS code ${selectedTariff}`, result);
      
      // Add to confirmed items
      confirmedItems.add(key);
      confirmedItems = confirmedItems; // Trigger reactivity
    } catch (error) {
      console.error("Error confirming item:", error);
      alert("Fehler beim Speichern der Bestätigung. Bitte versuchen Sie es erneut.");
    }
  }

  async function confirmWholeCluster(cluster: any) {
    if (!cluster.tariff_suggestions || cluster.tariff_suggestions.length === 0) {
      alert("Keine Zollnummern-Vorschläge für diesen Cluster vorhanden.");
      return;
    }

    const topSuggestion = cluster.tariff_suggestions[0];
    const clusterId = cluster.cluster_id;

    confirmingClusters.add(clusterId);
    confirmingClusters = confirmingClusters;

    try {
      // Confirm all items in the cluster with the top suggestion
      const confirmPromises = cluster.items.map(async (item: any) => {
        const key = `${clusterId}-${item.item_id}`;
        
        // Set the selection for this item
        itemSelections[key] = topSuggestion.tariff_code;
        itemConfidenceScores[key] = topSuggestion.confidence_score;
        
        // Confirm via API
        const response = await fetch(`${API_URL}/confirmations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            material_number: item.item_id,
            cluster_id: clusterId,
            assigned_tariff_code: topSuggestion.tariff_code,
            confidence_score: topSuggestion.confidence_score
          })
        });

        if (!response.ok) {
          throw new Error(`Failed to confirm ${item.item_id}`);
        }

        // Add to confirmed items
        confirmedItems.add(key);
        
        return response.json();
      });

      await Promise.all(confirmPromises);
      
      // Mark cluster as confirmed
      confirmedClusters.add(clusterId);
      confirmedClusters = confirmedClusters;
      confirmedItems = confirmedItems;
      itemSelections = itemSelections;

      console.log(`Confirmed entire cluster ${clusterId} with ${cluster.items.length} items using HS code ${topSuggestion.tariff_code}`);
    } catch (error) {
      console.error("Error confirming cluster:", error);
      alert("Fehler beim Bestätigen des Clusters. Bitte versuchen Sie es erneut.");
    } finally {
      confirmingClusters.delete(clusterId);
      confirmingClusters = confirmingClusters;
    }
  }

  function isClusterConfirmed(clusterId: string): boolean {
    return confirmedClusters.has(clusterId);
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
</script>

<div class="border border-gray-200 bg-white shadow-sm rounded-lg overflow-hidden">
  <div class="p-6 border-b border-gray-200 bg-gray-50">
    <h2 class="text-xl font-semibold text-[#272425]">Detaillierte Ergebnisse</h2>
    <p class="text-sm text-[#6b6b6b] mt-1">
      Vollständige Übersicht aller analysierten Produkte mit zugeteilten 8-stelligen Zollnummern
    </p>
    <div class="mt-3 bg-blue-50 border border-blue-200 rounded-md p-3">
      <p class="text-xs text-blue-800">
        <strong>Tipp:</strong> Sie können entweder alle Artikel eines Clusters auf einmal mit dem Top-Vorschlag bestätigen, 
        oder jeden Artikel einzeln mit Ihrer Wahl bestätigen.
      </p>
    </div>
  </div>

  {#if loading}
    <div class="p-12 text-center">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#BB1E38]"></div>
      <p class="mt-4 text-[#6b6b6b]">Lade Cluster-Daten...</p>
    </div>
  {:else if clusters.length === 0}
    <div class="p-12 text-center text-[#6b6b6b]">
      <AlertTriangle class="mx-auto h-12 w-12 mb-4 text-gray-400" />
      <p>Keine Cluster gefunden.</p>
    </div>
  {:else}
    <div class="divide-y divide-gray-200">
      {#each clusters as cluster (cluster.cluster_id)}
        {@const clusterConfirmed = isClusterConfirmed(cluster.cluster_id)}
        <div class="hover:bg-gray-50 transition-colors {clusterConfirmed ? 'bg-green-50/30' : ''}">
          <!-- Cluster Header -->
          <button
            on:click={() => toggleCluster(cluster.cluster_id)}
            class="w-full px-6 py-4 flex items-center justify-between text-left focus:outline-none focus:bg-gray-100"
          >
            <div class="flex items-center gap-4 flex-1">
              <div class="flex-shrink-0">
                {#if expandedClusters.has(cluster.cluster_id)}
                  <ChevronDown class="h-5 w-5 text-gray-500" />
                {:else}
                  <ChevronRight class="h-5 w-5 text-gray-500" />
                {/if}
              </div>
              
              <div class="flex-1">
                <div class="flex items-center gap-3">
                  <h3 class="text-lg font-semibold text-[#272425]">{cluster.cluster_name}</h3>
                  <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {cluster.item_count} {cluster.item_count === 1 ? 'Artikel' : 'Artikel'}
                  </span>
                  <span class="px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusBadge(cluster.status).class}">
                    {getStatusBadge(cluster.status).label}
                  </span>
                  {#if clusterConfirmed}
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 flex items-center gap-1">
                      <CheckCircle class="h-3 w-3" />
                      Bestätigt
                    </span>
                  {/if}
                </div>
                
                {#if cluster.tariff_suggestions && cluster.tariff_suggestions.length > 0}
                  <div class="mt-2 flex items-center gap-2 text-sm">
                    <span class="text-[#6b6b6b]">Vorgeschlagener HS-Code:</span>
                    <span class="font-mono font-semibold text-[#BB1E38]">
                      {cluster.tariff_suggestions[0].tariff_code}
                    </span>
                    <span class="px-2 py-0.5 rounded text-xs font-medium {getConfidenceBadge(cluster.tariff_suggestions[0].confidence_score)}">
                      {Math.round(cluster.tariff_suggestions[0].confidence_score * 100)}% Konfidenz
                    </span>
                  </div>
                {/if}
              </div>
            </div>
          </button>

          <!-- Expanded Content -->
          {#if expandedClusters.has(cluster.cluster_id)}
            <div class="px-6 pb-6 bg-gray-50/50">
              <!-- Tariff Suggestions -->
              {#if cluster.tariff_suggestions && cluster.tariff_suggestions.length > 0}
                <div class="mb-6 bg-white rounded-lg border border-gray-200 p-4">
                  <div class="flex items-center justify-between mb-3">
                    <h4 class="font-semibold text-[#272425] flex items-center gap-2">
                      <CheckCircle class="h-5 w-5 text-green-600" />
                      LLM-Vorschläge für Zollnummern (Top 3)
                    </h4>
                    
                    {#if isClusterConfirmed(cluster.cluster_id)}
                      <div class="flex items-center gap-2 px-4 py-2 bg-green-100 text-green-800 rounded-md">
                        <CheckCircle class="h-5 w-5" />
                        <span class="font-semibold text-sm">Cluster bestätigt ({cluster.item_count} Artikel)</span>
                      </div>
                    {:else}
                      <button
                        on:click={() => confirmWholeCluster(cluster)}
                        disabled={isClusterConfirming(cluster.cluster_id)}
                        class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md
                               bg-[#BB1E38] hover:bg-[#9a1830] text-white
                               disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {#if isClusterConfirming(cluster.cluster_id)}
                          <div class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Bestätige...
                        {:else}
                          <CheckCircle class="h-4 w-4 mr-2" />
                          Alle Artikel mit Top-Vorschlag bestätigen
                        {/if}
                      </button>
                    {/if}
                  </div>
                  
                  <div class="space-y-3">
                    {#each getTopSuggestions(cluster.tariff_suggestions, 3) as suggestion, idx}
                      <div class="border-l-4 {idx === 0 ? 'border-green-500' : 'border-gray-300'} pl-4 py-2">
                        <div class="flex items-start justify-between">
                          <div class="flex-1">
                            <div class="flex items-center gap-3 mb-1">
                              <span class="font-mono text-lg font-bold text-[#272425]">
                                {suggestion.tariff_code}
                              </span>
                              <span class="px-2 py-0.5 rounded text-xs font-medium {getConfidenceBadge(suggestion.confidence_score)}">
                                {Math.round(suggestion.confidence_score * 100)}%
                              </span>
                              {#if idx === 0}
                                <span class="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                  Empfohlen
                                </span>
                              {/if}
                            </div>
                            {#if suggestion.section_info}
                              <p class="text-xs text-[#6b6b6b] mb-2">{suggestion.section_info}</p>
                            {/if}
                            <p class="text-sm text-[#272425]">{suggestion.reasoning}</p>
                          </div>
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Items in Cluster -->
              <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <div class="px-4 py-3 bg-gray-100 border-b border-gray-200">
                  <h4 class="font-semibold text-[#272425]">Artikel in diesem Cluster</h4>
                </div>
                
                <div class="overflow-x-auto">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                          Material-Nr.
                        </th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-48">
                          Beschreibung
                        </th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-64">
                          Zollnummer (Top 2)
                        </th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Details (Einkaufsbestelltext)
                        </th>
                        <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                          Bestätigen
                        </th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      {#each cluster.items as item}
                        {@const top2Suggestions = getTopSuggestions(cluster.tariff_suggestions || [], 2)}
                        {@const itemKey = `${cluster.cluster_id}-${item.item_id}`}
                        {@const isConfirmed = isItemConfirmed(cluster.cluster_id, item.item_id)}
                        {@const selectedTariff = getSelectedTariff(cluster.cluster_id, item.item_id)}
                        
                        <tr class="hover:bg-gray-50 {isConfirmed ? 'bg-green-50' : ''}">
                          <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-[#272425]">
                            {item.item_id}
                            {#if isConfirmed}
                              <CheckCircle class="inline h-4 w-4 text-green-600 ml-1" />
                            {/if}
                          </td>
                          <td class="px-4 py-3 text-sm text-[#6b6b6b]">
                            {item.raw_description}
                          </td>
                          <td class="px-4 py-3 text-sm">
                            {#if top2Suggestions.length > 0}
                              <div class="space-y-2">
                                {#each top2Suggestions as suggestion, idx}
                                  <label class="flex items-start gap-2 cursor-pointer hover:bg-gray-100 p-2 rounded {selectedTariff === suggestion.tariff_code ? 'bg-blue-50 border border-blue-300' : ''}">
                                    <input
                                      type="radio"
                                      name="tariff-{itemKey}"
                                      value={suggestion.tariff_code}
                                      disabled={isConfirmed}
                                      on:change={() => selectTariffForItem(cluster.cluster_id, item.item_id, suggestion.tariff_code, suggestion.confidence_score)}
                                      checked={selectedTariff === suggestion.tariff_code}
                                      class="mt-1 h-4 w-4 text-[#BB1E38] focus:ring-[#BB1E38] disabled:opacity-50"
                                    />
                                    <div class="flex-1">
                                      <div class="flex items-center gap-2">
                                        <span class="font-mono font-semibold text-[#272425]">
                                          {suggestion.tariff_code}
                                        </span>
                                        <span class="px-1.5 py-0.5 rounded text-xs {getConfidenceBadge(suggestion.confidence_score)}">
                                          {Math.round(suggestion.confidence_score * 100)}%
                                        </span>
                                        {#if idx === 0}
                                          <span class="px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-800">
                                            Empfohlen
                                          </span>
                                        {/if}
                                      </div>
                                    </div>
                                  </label>
                                {/each}
                              </div>
                            {:else}
                              <span class="text-gray-400 text-xs">Keine Vorschläge</span>
                            {/if}
                          </td>
                          <td class="px-4 py-3 text-sm text-[#6b6b6b] max-w-xs">
                            <div class="whitespace-pre-wrap text-xs leading-relaxed">
                              {item.purchase_order_text || 'Keine Details verfügbar'}
                            </div>
                          </td>
                          <td class="px-4 py-3 text-center">
                            <button
                              on:click={() => confirmItem(cluster.cluster_id, item.item_id)}
                              disabled={isConfirmed || !selectedTariff}
                              class="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium rounded-md
                                     {isConfirmed 
                                       ? 'bg-green-600 text-white cursor-default' 
                                       : selectedTariff
                                         ? 'bg-[#BB1E38] hover:bg-[#9a1830] text-white'
                                         : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                     }
                                     disabled:opacity-75 transition-colors"
                            >
                              {#if isConfirmed}
                                <CheckCircle class="h-4 w-4 mr-1" />
                                Bestätigt
                              {:else}
                                Bestätigen
                              {/if}
                            </button>
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
