<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { Alert } from "flowbite-svelte";
  import { ArrowLeft, CheckCircle } from "lucide-svelte";
  
  import AnalysisOverview from "$lib/components/AnalysisOverview.svelte";
  import ConfidenceOverview from "$lib/components/ConfidenceOverview.svelte";
  import ClusterResults from "$lib/components/ClusterResults.svelte";

  let clusters: any[] = [];
  let loading = true;
  let errorMsg = "";
  let isConfirmed = false;

  const API_URL = "http://localhost:8000";

  async function fetchClusters() {
    loading = true;
    errorMsg = "";
    try {
      const res = await fetch(`${API_URL}/clusters/enriched?auto_generate=true`);
      if (!res.ok) throw new Error("Failed to load clusters");
      clusters = await res.json();
      console.log("Loaded clusters:", clusters);
    } catch (err) {
      console.error("Error fetching clusters:", err);
      errorMsg = "Fehler beim Laden der Cluster-Daten. Bitte stellen Sie sicher, dass das Backend läuft.";
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchClusters();
  });

  function handleBack() {
    goto("/");
  }

  function handleConfirmAndProceed() {
    if (isConfirmed) {
      console.log("Bestätigen und fortfahren clicked");
      // TODO: Export data or navigate to next step
    }
  }

  // Calculate stats from clusters for overview components
  $: totalItems = clusters.reduce((sum, c) => sum + c.item_count, 0);
  $: analyzedClusters = clusters.filter(c => c.status === 'completed').length;

</script>

<div class="min-h-screen bg-white">
  <div class="max-w-7xl mx-auto px-8 py-12">
    <!-- Header with Back Button -->
    <div class="mb-12">
      <div class="flex items-center gap-3 mb-3">
        <button
          on:click={handleBack}
          class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-gray-300 bg-transparent hover:bg-gray-50 h-9 px-3"
        >
          <ArrowLeft class="h-4 w-4 mr-2" />
          Zurück
        </button>
        <h1 class="text-4xl text-[#BB1E38] font-bold">Analyseergebnisse</h1>
      </div>
      <p class="text-base text-[#6b6b6b]">Ergebnisse der HS-Code-Zuordnung</p>
    </div>

    {#if errorMsg}
      <Alert color="red" class="mb-8 shadow-sm">{errorMsg}</Alert>
    {/if}

    <div class="space-y-8">
      <!-- KPI Overview -->
      <AnalysisOverview {clusters} {loading} />

      <!-- Confidence Level Overview -->
      <ConfidenceOverview {clusters} {loading} />

      <!-- Info Banner -->
      {#if !loading && clusters.length > 0}
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div class="flex items-start gap-3">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-blue-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div class="flex-1">
              <h3 class="text-sm font-semibold text-blue-900">Cluster-basierte Analyse</h3>
              <p class="text-sm text-blue-800 mt-1">
                Produkte wurden in <strong>{clusters.length} Cluster</strong> gruppiert mit insgesamt <strong>{totalItems} Artikeln</strong>. 
                {analyzedClusters} Cluster wurden erfolgreich analysiert und haben LLM-Vorschläge für HS-Codes.
              </p>
            </div>
          </div>
        </div>
      {/if}

      <!-- Cluster Results -->
      <ClusterResults {clusters} {loading} />


      <!-- Manual Confirmation Section -->
      <div class="border-2 border-[#BB1E38] bg-red-50/20 shadow-sm rounded-lg overflow-hidden">
        <div class="p-6 border-b border-[#BB1E38]/10">
          <h3 class="text-xl font-semibold text-[#272425]">Manuelle Bestätigung</h3>
          <p class="text-[#6b6b6b] mt-1 text-sm">
            Bitte überprüfen Sie alle Ergebnisse mit erforderlichem User Input, bevor Sie fortfahren
          </p>
        </div>
        <div class="p-6">
          <div class="space-y-4">
            <div class="flex items-start space-x-3 bg-white p-5 rounded-lg border border-gray-200">
              <input
                type="checkbox"
                id="confirm-review"
                bind:checked={isConfirmed}
                class="w-5 h-5 mt-0.5 rounded border-gray-300 text-[#BB1E38] focus:ring-[#BB1E38]"
              />
              <div class="grid gap-1.5 leading-none flex-1">
                <label
                  for="confirm-review"
                  class="text-sm font-medium leading-relaxed cursor-pointer text-[#272425]"
                >
                  Ich bestätige, dass alle Einträge mit „User Input notwendig" sowie alle Tarif-Warnungen überprüft wurden.
                </label>
                <p class="text-sm text-[#6b6b6b] leading-relaxed">
                  Nur vollständig bestätigte 8-stellige Zollnummern können im nächsten Schritt exportiert werden.
                </p>
              </div>
            </div>
            
            <div class="flex justify-end gap-3 mt-4">
              <button
                on:click={handleBack}
                class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-gray-300 bg-white hover:bg-gray-50 h-10 px-4 py-2"
              >
                Abbrechen
              </button>
              <button
                on:click={handleConfirmAndProceed}
                disabled={!isConfirmed}
                class="inline-flex items-center justify-center rounded-md text-sm font-medium h-10 px-4 py-2 bg-[#BB1E38] hover:bg-[#9a1830] disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
              >
                <CheckCircle class="mr-2 h-4 w-4" />
                Bestätigen und fortfahren
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
