<script lang="ts">
  import { BarChart2, TrendingUp } from "lucide-svelte";

  export let clusters: any[] = [];
  export let loading: boolean = false;

  // Calculate confidence distribution
  $: veryHighConfidence = clusters.filter(c => 
    c.tariff_suggestions && c.tariff_suggestions.length > 0 && c.tariff_suggestions[0].confidence_score >= 0.9
  ).length;
  
  $: highConfidence = clusters.filter(c => 
    c.tariff_suggestions && c.tariff_suggestions.length > 0 && 
    c.tariff_suggestions[0].confidence_score >= 0.8 && c.tariff_suggestions[0].confidence_score < 0.9
  ).length;
  
  $: mediumConfidence = clusters.filter(c => 
    c.tariff_suggestions && c.tariff_suggestions.length > 0 && 
    c.tariff_suggestions[0].confidence_score >= 0.5 && c.tariff_suggestions[0].confidence_score < 0.8
  ).length;
  
  $: lowConfidence = clusters.filter(c => 
    c.tariff_suggestions && c.tariff_suggestions.length > 0 && c.tariff_suggestions[0].confidence_score < 0.5
  ).length;

  $: totalWithSuggestions = veryHighConfidence + highConfidence + mediumConfidence + lowConfidence;

</script>

<div class="border shadow-sm bg-white rounded-lg overflow-hidden">
  <div class="p-6 border-b border-gray-100">
    <h3 class="text-xl font-semibold text-[#BB1E38]">Konfidenz-Übersicht</h3>
    <p class="text-sm text-[#6b6b6b] mt-1">
      Verteilung der Cluster nach Konfidenz-Level der LLM-Vorschläge
    </p>
  </div>
  <div class="p-6">
    {#if totalWithSuggestions > 0}
      <div class="space-y-4">
        <!-- Very High Confidence -->
        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-green-600"></div>
              <span class="text-sm font-medium text-green-900">Sehr hohe Konfidenz (≥90%)</span>
            </div>
            <span class="text-lg font-bold text-green-900">{veryHighConfidence}</span>
          </div>
          <div class="w-full bg-green-200 rounded-full h-2">
            <div class="bg-green-600 h-full rounded-full transition-all duration-300" style="width: {totalWithSuggestions > 0 ? (veryHighConfidence / totalWithSuggestions) * 100 : 0}%"></div>
          </div>
        </div>

        <!-- High Confidence -->
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-blue-600"></div>
              <span class="text-sm font-medium text-blue-900">Hohe Konfidenz (80-89%)</span>
            </div>
            <span class="text-lg font-bold text-blue-900">{highConfidence}</span>
          </div>
          <div class="w-full bg-blue-200 rounded-full h-2">
            <div class="bg-blue-600 h-full rounded-full transition-all duration-300" style="width: {totalWithSuggestions > 0 ? (highConfidence / totalWithSuggestions) * 100 : 0}%"></div>
          </div>
        </div>

        <!-- Medium Confidence -->
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-yellow-600"></div>
              <span class="text-sm font-medium text-yellow-900">Mittlere Konfidenz (50-79%)</span>
            </div>
            <span class="text-lg font-bold text-yellow-900">{mediumConfidence}</span>
          </div>
          <div class="w-full bg-yellow-200 rounded-full h-2">
            <div class="bg-yellow-600 h-full rounded-full transition-all duration-300" style="width: {totalWithSuggestions > 0 ? (mediumConfidence / totalWithSuggestions) * 100 : 0}%"></div>
          </div>
        </div>

        <!-- Low Confidence -->
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-red-600"></div>
              <span class="text-sm font-medium text-red-900">Niedrige Konfidenz (&lt;50%)</span>
            </div>
            <span class="text-lg font-bold text-red-900">{lowConfidence}</span>
          </div>
          <div class="w-full bg-red-200 rounded-full h-2">
            <div class="bg-red-600 h-full rounded-full transition-all duration-300" style="width: {totalWithSuggestions > 0 ? (lowConfidence / totalWithSuggestions) * 100 : 0}%"></div>
          </div>
        </div>
      </div>

      <!-- Summary Note -->
      <div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p class="text-sm text-blue-900">
          <span class="font-medium">Hinweis:</span> Cluster mit sehr hoher Konfidenz (≥90%) haben verlässliche HS-Code-Vorschläge. 
          Alle anderen sollten manuell überprüft werden.
        </p>
      </div>
    {:else}
      <div class="p-12 text-center text-[#6b6b6b]">
        <BarChart2 class="mx-auto h-12 w-12 mb-4 text-gray-400" />
        <p>Keine Konfidenz-Daten verfügbar.</p>
        <p class="text-sm mt-2">Warten auf LLM-Analyse...</p>
      </div>
    {/if}
  </div>
</div>
