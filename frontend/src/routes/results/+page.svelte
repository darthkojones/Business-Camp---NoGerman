<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { Alert } from "flowbite-svelte";
  import { CheckCircle } from "lucide-svelte";

  import AnalysisOverview from "$lib/components/AnalysisOverview.svelte";
  // import ConfidenceOverview from "$lib/components/ConfidenceOverview.svelte";
  import ClusterResults from "$lib/components/ClusterResults.svelte";
  import NavigationHeader from "$lib/components/NavigationHeader.svelte";

  let clusters: any[] = [];
  let loading = true;
  let errorMsg = "";

  const API_URL = "http://localhost:8000";

  async function fetchClusters() {
    loading = true;
    errorMsg = "";
    try {
      const res = await fetch(
        `${API_URL}/clusters/enriched?auto_generate=true`,
      );
      if (!res.ok) throw new Error("Failed to load clusters");
      clusters = await res.json();
      console.log("Loaded clusters:", clusters);
    } catch (err) {
      console.error("Error fetching clusters:", err);
      errorMsg =
        "Fehler beim Laden der Cluster-Daten. Bitte stellen Sie sicher, dass das Backend läuft.";
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchClusters();
  });

  // Calculate stats from clusters for overview components
  $: totalItems = clusters.reduce((sum, c) => sum + c.item_count, 0);
  $: analyzedClusters = clusters.filter((c) => c.status === "completed").length;
</script>

<div class="min-h-screen bg-white">
  <div class="max-w-7xl mx-auto px-8 py-12">
    <!-- Step navigation header -->
    <NavigationHeader currentStep={2} />

    <!-- Page title -->
    <div class="mb-12">
      <h1 class="text-4xl text-[#BB1E38] font-bold">Analyseergebnisse</h1>
      <p class="text-base text-[#6b6b6b]">Ergebnisse der HS-Code-Zuordnung</p>
    </div>

    {#if errorMsg}
      <Alert color="red" class="mb-8 shadow-sm">{errorMsg}</Alert>
    {/if}

    <div class="space-y-8">
      <!-- KPI Overview -->
      <AnalysisOverview {clusters} {loading} />

      <!-- Confidence Level Overview -->
      <!-- <ConfidenceOverview {clusters} {loading} /> -->

      <!-- Info Banner -->
      {#if !loading && clusters.length > 0}
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div class="flex items-start gap-3">
            <div class="flex-shrink-0">
              <svg
                class="h-5 w-5 text-blue-600 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div class="flex-1">
              <h3 class="text-sm font-semibold text-blue-900">
                Cluster-basierte Analyse
              </h3>
              <p class="text-sm text-blue-800 mt-1">
                Produkte wurden in <strong>{clusters.length} Cluster</strong>
                gruppiert mit insgesamt <strong>{totalItems} Artikeln</strong>.
                {analyzedClusters} Cluster wurden erfolgreich analysiert und haben
                LLM-Vorschläge für HS-Codes.
              </p>
            </div>
          </div>
        </div>
      {/if}

      <!-- Cluster Results -->
      <ClusterResults {clusters} {loading} />
    </div>
  </div>
</div>
