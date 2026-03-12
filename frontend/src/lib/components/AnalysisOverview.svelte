<script lang="ts">
  import { AlertTriangle, FileCheck, CheckCircle, AlertCircle, BarChart3 } from "lucide-svelte";

  export let clusters: any[] = [];
  export let loading: boolean = false;

  // Calculate KPIs from clusters
  $: totalItems = clusters.reduce((sum, c) => sum + c.item_count, 0);
  $: analyzedClusters = clusters.filter(c => c.status === 'completed').length;
  $: highConfidenceClusters = clusters.filter(c => 
    c.tariff_suggestions && c.tariff_suggestions.length > 0 && c.tariff_suggestions[0].confidence_score >= 0.8
  ).length;
  $: needsReviewClusters = clusters.filter(c => 
    c.status === 'error' || (c.tariff_suggestions && c.tariff_suggestions.length > 0 && c.tariff_suggestions[0].confidence_score < 0.8)
  ).length;
  $: accuracyRate = clusters.length > 0 ? Math.round((analyzedClusters / clusters.length) * 100) : 0;

</script>

<div class="border shadow-sm bg-white rounded-lg overflow-hidden relative">
  <div class="p-6 border-b border-gray-100">
    <h3 class="text-xl font-semibold text-[#BB1E38]">Letzte Dateianalyse</h3>
    <div class="flex items-center gap-2 mt-1 text-sm text-[#6b6b6b]">
      <FileCheck class="h-4 w-4" />
      <span>{clusters.length > 0 ? `${clusters.length} Cluster analysiert` : loading ? "Loading..." : "No Data"}</span>
      <span class="text-gray-400">•</span>
      <span>{new Date().toLocaleDateString('de-DE')}</span>
    </div>
  </div>

  <div class="p-6">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <!-- Total Items -->
      <div class="bg-gray-50 rounded-lg p-6 border border-gray-200">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm text-[#6b6b6b] mb-2">Gesamtzahl</p>
            <p class="text-3xl text-[#272425] font-semibold mb-1">{totalItems || "--"}</p>
            <p class="text-xs text-[#6b6b6b]">Artikel in {clusters.length} Clustern</p>
          </div>
          <div class="bg-gray-200 p-2.5 rounded-lg">
            <FileCheck class="h-5 w-5 text-gray-600" />
          </div>
        </div>
      </div>

      <!-- Secure Assignments -->
      <div class="bg-green-50 rounded-lg p-6 border border-green-200">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm text-green-700 mb-2">Hohe Konfidenz</p>
            <p class="text-3xl text-green-900 font-semibold mb-1">{highConfidenceClusters}</p>
            <p class="text-xs text-green-700">({clusters.length > 0 ? Math.round((highConfidenceClusters / clusters.length) * 100) : 0}% der Cluster)</p>
          </div>
          <div class="bg-green-200 p-2.5 rounded-lg">
            <CheckCircle class="h-5 w-5 text-green-700" />
          </div>
        </div>
      </div>

      <!-- Needs Input -->
      <div class="bg-red-50 rounded-lg p-6 border border-red-200">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm text-[#BB1E38] mb-2">Überprüfung nötig</p>
            <p class="text-3xl text-red-900 font-semibold mb-1">{needsReviewClusters}</p>
            <p class="text-xs text-[#BB1E38]">({clusters.length > 0 ? Math.round((needsReviewClusters / clusters.length) * 100) : 0}% der Cluster)</p>
          </div>
          <div class="bg-red-200 p-2.5 rounded-lg">
            <AlertCircle class="h-5 w-5 text-[#BB1E38]" />
          </div>
        </div>
      </div>

      <!-- Accuracy -->
      <div class="bg-blue-50 rounded-lg p-6 border border-blue-200">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm text-blue-700 mb-2">Analysiert</p>
            <p class="text-3xl text-blue-900 font-semibold mb-1">{accuracyRate}%</p>
            <p class="text-xs text-blue-700">{analyzedClusters} von {clusters.length}</p>
          </div>
          <div class="bg-blue-200 p-2.5 rounded-lg">
            <BarChart3 class="h-5 w-5 text-blue-700" />
          </div>
        </div>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="mt-6">
      <div class="flex items-center justify-between text-sm mb-2">
        <span class="text-[#6b6b6b]">Fortschritt: Cluster mit hoher Konfidenz</span>
        <span class="text-[#272425] font-medium">{clusters.length > 0 ? Math.round((highConfidenceClusters / clusters.length) * 100) : 0}%</span>
      </div>
      <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div class="bg-green-500 h-full transition-all duration-300" style="width: {clusters.length > 0 ? Math.round((highConfidenceClusters / clusters.length) * 100) : 0}%"></div>
      </div>
    </div>
  </div>
</div>
