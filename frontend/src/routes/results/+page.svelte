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

  // cache of confirmed material numbers loaded from backend
  let confirmedMaterials: Set<string> = new Set();

  // whether we can already jump to overview/export
  let canAdvance = false;
  $: navStep = canAdvance ? 3 : 2;

  const API_URL = "http://localhost:8000";

  async function fetchClusters() {
    loading = true;
    errorMsg = "";
    try {
      const res = await fetch(
        `${API_URL}/clusters/enriched?auto_generate=true`,
      );
      if (!res.ok) throw new Error("Failed to load clusters");
      let data = await res.json();
      console.log("Loaded clusters:", data);

      // filter out clusters where all items have been confirmed already
      if (confirmedMaterials.size > 0) {
        data = data.filter((c: any) => {
          if (!c.items || c.items.length === 0) return true;
          // keep cluster if at least one item is unconfirmed
          return c.items.some(
            (item: any) => !confirmedMaterials.has(item.item_id),
          );
        });
      }
      clusters = data;
    } catch (err) {
      console.error("Error fetching clusters:", err);
      errorMsg =
        "Fehler beim Laden der Cluster-Daten. Bitte stellen Sie sicher, dass das Backend läuft.";
    } finally {
      loading = false;
    }
  }

  async function fetchConfirmedMaterials() {
    try {
      const res = await fetch(`${API_URL}/confirmations`);
      if (!res.ok) return;
      const items = await res.json();
      confirmedMaterials = new Set(items.map((i: any) => i.material_number));
      console.log("Confirmed materials loaded:", confirmedMaterials);
    } catch (e) {
      console.error("Error fetching confirmed materials", e);
    }
  }

  onMount(async () => {
    await fetchConfirmedMaterials();
    await fetchClusters();
  });

  // Calculate stats from clusters for overview components
  $: totalItems = clusters.reduce((sum, c) => sum + c.item_count, 0);
  $: analyzedClusters = clusters.filter((c) => c.status === "completed").length;
</script>

<div class="min-h-screen bg-white">
  <div class="max-w-7xl mx-auto px-8 py-12">
    <!-- Step navigation header -->
    <NavigationHeader currentStep={navStep} />

    <!-- Page title -->
    <div class="mb-12">
      <h1 class="text-4xl text-[#BB1E38] font-bold">Analyseergebnisse</h1>
    </div>

    {#if errorMsg}
      <Alert color="red" class="mb-8 shadow-sm">{errorMsg}</Alert>
    {/if}

    <div class="space-y-8">
      <!-- KPI Overview -->
      <AnalysisOverview {clusters} {loading} />

      <!-- Confidence Level Overview -->
      <!-- <ConfidenceOverview {clusters} {loading} /> -->

      <!-- Cluster Results -->
      <ClusterResults
        {clusters}
        {loading}
        on:progress={() => (canAdvance = true)}
      />
    </div>
  </div>
</div>
