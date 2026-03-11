<script lang="ts">
  import { onMount } from "svelte";
  import { Alert } from "flowbite-svelte";
  import { ArrowLeft, CheckCircle } from "lucide-svelte";
  
  import AnalysisOverview from "$lib/components/AnalysisOverview.svelte";
  import ConfidenceOverview from "$lib/components/ConfidenceOverview.svelte";
  import ResultsTable from "$lib/components/ResultsTable.svelte";

  let materials: any[] = [];
  let loading = true;
  let errorMsg = "";
  let isConfirmed = false;

  const API_URL = "http://localhost:8000";

  async function fetchMaterials() {
    loading = true;
    try {
      const res = await fetch(`${API_URL}/materials`);
      if (!res.ok) throw new Error("Failed to load materials");
      materials = await res.json();
    } catch (err) {
      errorMsg = "Failed to load materials.";
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchMaterials();
  });

  function handleBack() {
    // Navigate back or to home
    console.log("Zurück clicked");
  }

  function handleConfirmAndProceed() {
    if (isConfirmed) {
      console.log("Bestätigen und fortfahren clicked");
    }
  }
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
      <AnalysisOverview {materials} {loading} />

      <!-- Confidence Level Overview -->
      <ConfidenceOverview />

      <!-- Results Table -->
      <ResultsTable {materials} {loading} />

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
