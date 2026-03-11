<script lang="ts">
  import { AlertTriangle } from "lucide-svelte";
</script>

<div class="border shadow-sm bg-white rounded-lg overflow-hidden">
  <div class="p-6 border-b border-gray-100">
    <h3 class="text-xl font-semibold text-[#BB1E38]">Konfidenz-Übersicht</h3>
    <p class="text-sm text-[#6b6b6b] mt-1">
      Verteilung der Materialien nach Sicherheitsstufen der automatischen Zuordnung
    </p>
  </div>
  <div class="p-6">
    <div class="p-6 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-4">
      <AlertTriangle class="h-6 w-6 text-yellow-600 flex-shrink-0 mt-0.5" />
      <div>
        <h4 class="text-base font-semibold text-yellow-800">Datenaggregation fehlt im Backend</h4>
        <p class="text-sm text-yellow-700 mt-2 leading-relaxed">
          Aktuell liefert das Backend (<code>/materials</code>) noch keine aggregierten Metriken zur Konfidenz (z.B. "8 von 8 Ziffern sicher"). 
          Sobald weitere KI-Logik (Klassifikation & Scoring) angebunden ist, erscheint hier die detaillierte Aufschlüsselung der Sicherheitsstufen analog zum UI-Entwurf.
        </p>
      </div>
    </div>

    <!-- Summary Note (from sketch) -->
    <div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg opacity-60">
      <p class="text-sm text-blue-900">
        <span class="font-medium">Hinweis:</span> Nur Materialien in der Gruppe „8 von 8" dürfen direkt weiterverarbeitet werden. 
        Alle anderen Gruppen müssen zuerst geprüft, ergänzt und bestätigt werden.
      </p>
    </div>
  </div>
</div>
