<script lang="ts">
  import { ChevronDown, ChevronRight, CheckCircle, AlertTriangle, HelpCircle } from "lucide-svelte";

  export let clusters: any[] = [];
  export let loading: boolean = false;

  let expandedClusters: Set<string> = new Set();
  
  // Track user selections and confirmations for each item
  // Format: { "clusterId-itemId": "tariff_code" }
  let itemSelections: Record<string, string> = {};
  
  // Format: Set of "clusterId-itemId" for confirmed items
  let confirmedItems: Set<string> = new Set();

  function toggleCluster(clusterId: string) {
    if (expandedClusters.has(clusterId)) {
      expandedClusters.delete(clusterId);
    } else {
      expandedClusters.add(clusterId);
    }
    expandedClusters = expandedClusters; // Trigger reactivity
  }

  function selectTariffForItem(clusterId: string, itemId: string, tariffCode: string) {
    const key = `${clusterId}-${itemId}`;
    itemSelections[key] = tariffCode;
    itemSelections = itemSelections; // Trigger reactivity
  }

  function confirmItem(clusterId: string, itemId: string) {
    const key = `${clusterId}-${itemId}`;
    if (itemSelections[key]) {
      confirmedItems.add(key);
      confirmedItems = confirmedItems; // Trigger reactivity
      console.log(`Confirmed: Material ${itemId} with HS code ${itemSelections[key]}`);
    }
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
        <div class="hover:bg-gray-50 transition-colors">
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
                  <h4 class="font-semibold text-[#272425] mb-3 flex items-center gap-2">
                    <CheckCircle class="h-5 w-5 text-green-600" />
                    LLM-Vorschläge für Zollnummern (Top 3)
                  </h4>
                  
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
                                      on:change={() => selectTariffForItem(cluster.cluster_id, item.item_id, suggestion.tariff_code)}
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
