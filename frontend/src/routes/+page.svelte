<script lang="ts">
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import { Upload, FileText, AlertCircle } from "lucide-svelte";
  import { Alert } from "flowbite-svelte";
  import NavigationHeader from "$lib/components/NavigationHeader.svelte";

  const API_URL = "http://localhost:8000";

  let materialsFile: File | null = null;
  let uploading = false;
  let processing = false;
  let uploadSuccess = false;
  let errorMsg = "";
  let statusMsg = "";
  let materialsCount = 0;
  let tariffsCount = 0; // will reflect current loaded tariff count (pre-seeded)

  onMount(async () => {
    try {
      const res = await fetch(`${API_URL}/tariffs/count`);
      if (res.ok) {
        const data = await res.json();
        tariffsCount = data.count || 0;
      }
    } catch (err) {
      console.error("Failed to fetch tariff count", err);
    }
  });

  function handleMaterialsFileChange(event: Event) {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      materialsFile = target.files[0];
    }
  }

  async function uploadFiles() {
    if (!materialsFile) {
      errorMsg = "Bitte wählen Sie mindestens eine Material-Datei aus.";
      return;
    }

    uploading = true;
    errorMsg = "";
    statusMsg = "Dateien werden hochgeladen...";

    try {
      const formData = new FormData();
      if (materialsFile) formData.append("materials_file", materialsFile);
      // customs_file is no longer required; tariff codes are seeded from the built-in CSV

      const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Upload fehlgeschlagen");
      }

      const result = await res.json();
      materialsCount = result.materials_count || 0;
      tariffsCount = result.tariffs_count || 0;
      uploadSuccess = true;
      statusMsg = "Dateien erfolgreich hochgeladen!";
    } catch (err: any) {
      errorMsg = err.message || "Fehler beim Hochladen der Dateien.";
      uploadSuccess = false;
    } finally {
      uploading = false;
    }
  }

  // helper that performs upload and, on success, immediately kicks off analysis
  async function uploadAndAnalyze() {
    await uploadFiles();
    if (uploadSuccess) {
      await startAnalysis();
    }
  }

  async function startAnalysis() {
    processing = true;
    errorMsg = "";
    statusMsg = "Clustering und LLM-Analyse werden gestartet...";

    try {
      const res = await fetch(`${API_URL}/process`, {
        method: "POST",
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Analyse fehlgeschlagen");
      }

      const result = await res.json();
      statusMsg = `Analyse abgeschlossen! ${result.clusters_count || 0} Cluster erstellt.`;

      // Navigate to results page after a short delay
      setTimeout(() => {
        goto("/results");
      }, 1500);
    } catch (err: any) {
      errorMsg = err.message || "Fehler bei der Analyse.";
      processing = false;
    }
  }
</script>

<div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
  <div class="max-w-5xl mx-auto px-8 py-12">
    <NavigationHeader currentStep={1} />

    <!-- Header -->
    <div class="text-center mb-12">
      <h1 class="text-5xl font-bold text-[#BB1E38] mb-4">
        Zollnummern Zuordnungs Werkzeug
      </h1>
    </div>

    {#if errorMsg}
      <Alert color="red" class="mb-6">{errorMsg}</Alert>
    {/if}

    {#if statusMsg && !errorMsg}
      <Alert color="green" class="mb-6">{statusMsg}</Alert>
    {/if}

    <!-- Upload Section -->
    <div class="bg-white rounded-xl shadow-lg p-8 mb-8">
      <div class="grid gap-6 justify-center">
        <!-- Materials File Upload -->
        <div
          class="border-2 border-dashed border-gray-300 rounded-lg p-6 hover:border-[#BB1E38] transition-colors mx-auto justify-center"
        >
          <div class="text-center">
            <FileText class="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 class="text-lg font-medium text-[#272425] mb-2">
              Materialien-Datei
            </h3>
            <p class="text-sm text-[#6b6b6b] mb-4">
              CSV-Datei mit Ihren Produkten und Materialnummern
            </p>
            <input
              type="file"
              accept=".csv"
              on:change={handleMaterialsFileChange}
              class="hidden"
              id="materials-upload"
              disabled={uploading || processing}
            />
            <label
              for="materials-upload"
              class="inline-flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 cursor-pointer disabled:opacity-50"
            >
              Datei auswählen
            </label>
            {#if materialsFile}
              <p class="mt-3 text-sm font-medium text-green-600">
                ✓ {materialsFile.name}
              </p>
            {/if}
          </div>
        </div>
      </div>

      <div class="mt-6">
        <button
          on:click={uploadAndAnalyze}
          disabled={!materialsFile || uploading || processing}
          class="w-full bg-[#BB1E38] hover:bg-[#9a1830] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {#if uploading || processing}
            <div
              class="animate-spin rounded-full h-5 w-5 border-b-2 border-white"
            ></div>
            {#if uploading}
              Hochladen...
            {:else}
              Analyse läuft...
            {/if}
          {:else}
            <Upload class="h-5 w-5" />
            Dateien hochladen & Analyse starten
          {/if}
        </button>
      </div>

      {#if uploadSuccess}
        <div class="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div class="flex items-start gap-3">
            <AlertCircle class="h-5 w-5 text-green-600 mt-0.5" />
            <div>
              <h4 class="text-sm font-semibold text-green-900">
                Upload erfolgreich!
              </h4>
              <p class="text-sm text-green-800 mt-1">
                {materialsCount > 0 && `${materialsCount} Materialien geladen.`}
                {tariffsCount > 0 &&
                  `Tarifdaten im System: ${tariffsCount} Einträge.`}
              </p>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
