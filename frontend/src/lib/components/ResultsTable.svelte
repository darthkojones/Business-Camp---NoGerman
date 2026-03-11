<script lang="ts">
  import { AlertCircle } from "lucide-svelte";
  import {
    Table,
    TableBody,
    TableBodyCell,
    TableBodyRow,
    TableHead,
    TableHeadCell,
    Badge,
  } from "flowbite-svelte";

  export let materials: any[] = [];
  export let loading: boolean = false;

  const formatHSCode = (code: string | null | undefined) => {
    if (!code) return "—";
    const paddedCode = code.padEnd(8, '0');
    return `${paddedCode.slice(0, 4)} ${paddedCode.slice(4, 8)}`;
  };
</script>

<div class="border shadow-sm bg-white rounded-lg overflow-hidden">
  <div class="p-6 border-b border-gray-100">
    <h3 class="text-xl font-semibold text-[#BB1E38]">Detaillierte Ergebnisse</h3>
    <p class="text-sm text-[#6b6b6b] mt-1">
      Vollständige Übersicht aller analysierten Produkte mit zugeteilten 8-stelligen Zollnummern
    </p>
  </div>
  
  <div class="p-4 bg-yellow-50 border-b border-yellow-200 flex items-start gap-3">
     <AlertCircle class="h-5 w-5 text-yellow-600 mt-0.5" />
     <div class="text-sm text-yellow-800">
       <span class="font-semibold">Backend Logic Needed:</span> 
       The current <code>/materials</code> endpoint only provides basic material data. 
       Fields like <strong>Suggested HS Code</strong>, <strong>Confidence</strong>, <strong>Warnings</strong>, and <strong>Status</strong> are currently missing from the data schema.
     </div>
  </div>

  <div class="relative overflow-x-auto">
    <Table hoverable={true} class="w-full text-left">
      <TableHead class="bg-gray-50/50 text-gray-700 text-xs">
        <TableHeadCell class="w-[50px] font-medium">Nr.</TableHeadCell>
        <TableHeadCell class="font-medium">Materialnummer</TableHeadCell>
        <TableHeadCell class="font-medium">Produktbeschreibung</TableHeadCell>
        <TableHeadCell class="font-medium min-w-[150px]">Zugewiesene Zollnummer</TableHeadCell>
        <TableHeadCell class="font-medium min-w-[150px]">Vorgeschlagene Zollnummer</TableHeadCell>
        <TableHeadCell class="text-center font-medium">Status / Konfidenz</TableHeadCell>
      </TableHead>
      <TableBody class="divide-y">
        {#if loading}
          <TableBodyRow>
            <TableBodyCell colspan={6} class="text-center py-8 text-gray-500 font-medium">
              Lade Daten...
            </TableBodyCell>
          </TableBodyRow>
        {:else if materials.length === 0}
          <TableBodyRow>
            <TableBodyCell colspan={6} class="text-center py-8 text-gray-500 font-medium">
              Keine Materialien gefunden.
            </TableBodyCell>
          </TableBodyRow>
        {:else}
          {#each materials as item, index}
            <TableBodyRow class="hover:bg-gray-50/50">
              <TableBodyCell class="text-[#6b6b6b]">{index + 1}</TableBodyCell>
              <TableBodyCell class="text-[#272425] font-medium">{item.material_number}</TableBodyCell>
              <TableBodyCell class="text-[#272425] max-w-[250px] truncate" title={item.short_text || item.purchase_order_text}>
                {item.short_text || item.purchase_order_text || "—"}
              </TableBodyCell>
              
              <TableBodyCell>
                {#if item.is_classified && item.tariff_code_id}
                  <code class="px-3 py-1.5 rounded text-sm font-mono bg-green-50 text-green-900 border border-green-200">
                    {formatHSCode(item.tariff_code_id.toString())}
                  </code>
                {:else}
                  <span class="text-gray-400 text-sm italic">Fehlt</span>
                {/if}
              </TableBodyCell>
              
              <TableBodyCell>
                 <span class="text-gray-400 text-xs italic bg-gray-50 px-2 py-1 rounded border border-gray-100">Logik fehlt</span>
              </TableBodyCell>
              
              <TableBodyCell class="text-center">
                 <div class="flex flex-col items-center gap-1">
                   <Badge color="yellow" class="text-xs">Ausstehend</Badge>
                   <span class="text-[10px] text-gray-400">Keine Konfidenzdaten</span>
                 </div>
              </TableBodyCell>
            </TableBodyRow>
          {/each}
        {/if}
      </TableBody>
    </Table>
  </div>
  
  <div class="p-4 border-t border-gray-100 flex items-center justify-between text-sm text-[#6b6b6b]">
    <span>Zeige {materials.length} Einträge</span>
  </div>
</div>
