<script lang="ts">
  import { AlertTriangle, FileCheck, CheckCircle, AlertCircle, BarChart3 } from "lucide-svelte";

  export let materials: any[] = [];
  export let loading: boolean = false;
</script>

<div class="border shadow-sm bg-white rounded-lg overflow-hidden relative">
  <div class="p-6 border-b border-gray-100">
    <h3 class="text-xl font-semibold text-[#BB1E38]">Letzte Dateianalyse</h3>
    <div class="flex items-center gap-2 mt-1 text-sm text-[#6b6b6b]">
      <FileCheck class="h-4 w-4" />
      <span>{materials.length > 0 ? "Backend Data" : loading ? "Loading..." : "No Data"}</span>
      <span class="text-gray-400">•</span>
      <span>{new Date().toLocaleDateString('de-DE')}</span>
    </div>
  </div>

  <div class="p-6">
    <div class="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
      <AlertTriangle class="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
      <div>
        <h4 class="text-sm font-medium text-yellow-800">Mehr Logik im Backend erforderlich</h4>
        <p class="text-sm text-yellow-700 mt-1">Die Berechnungen für sichere Zuordnungen und Genauigkeit erfordern weitere API-Endpunkte für den Analyse-Report.</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 opacity-60">
      <!-- Total Items -->
      <div class="bg-gray-50 rounded-lg p-6 border border-gray-200">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm text-[#6b6b6b] mb-2">Gesamtzahl</p>
            <p class="text-3xl text-[#272425] font-semibold mb-1">{materials.length || "--"}</p>
            <p class="text-xs text-[#6b6b6b]">analysierte Produkte</p>
          </div>
          <div class="bg-gray-200 p-2.5 rounded-lg">
            <FileCheck class="h-5 w-5 text-gray-600" />
          </div>
        </div>
      </div>

      <!-- Secure Assignments -->
      <div class="bg-green-50 rounded-lg p-6 border border-green-200 grayscale">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm text-green-700 mb-2">Sicher zugeordnet</p>
            <p class="text-3xl text-green-900 font-semibold mb-1">--</p>
            <p class="text-xs text-green-700">(--%)</p>
          </div>
          <div class="bg-green-200 p-2.5 rounded-lg">
            <CheckCircle class="h-5 w-5 text-green-700" />
          </div>
        </div>
      </div>

      <!-- Needs Input -->
      <div class="bg-red-50 rounded-lg p-6 border border-red-200 grayscale">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm text-[#BB1E38] mb-2">User Input notwendig</p>
            <p class="text-3xl text-red-900 font-semibold mb-1">--</p>
            <p class="text-xs text-[#BB1E38]">(--%)</p>
          </div>
          <div class="bg-red-200 p-2.5 rounded-lg">
            <AlertCircle class="h-5 w-5 text-[#BB1E38]" />
          </div>
        </div>
      </div>

      <!-- Accuracy -->
      <div class="bg-blue-50 rounded-lg p-6 border border-blue-200 grayscale">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm text-blue-700 mb-2">Genauigkeit</p>
            <p class="text-3xl text-blue-900 font-semibold mb-1">--%</p>
            <p class="text-xs text-blue-700">Analysequote</p>
          </div>
          <div class="bg-blue-200 p-2.5 rounded-lg">
            <BarChart3 class="h-5 w-5 text-blue-700" />
          </div>
        </div>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="mt-6 opacity-60 grayscale">
      <div class="flex items-center justify-between text-sm mb-2">
        <span class="text-[#6b6b6b]">Fortschritt: Sicher zugeordnet</span>
        <span class="text-[#272425] font-medium">--%</span>
      </div>
      <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div class="bg-green-500 h-full transition-all duration-300" style="width: 0%"></div>
      </div>
    </div>
  </div>
</div>
