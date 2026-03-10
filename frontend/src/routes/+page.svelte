<script lang="ts">
  import { onMount } from "svelte";
  import {
    Table,
    TableBody,
    TableBodyCell,
    TableBodyRow,
    TableHead,
    TableHeadCell,
    Alert,
  } from "flowbite-svelte";

  let materials: any[] = [];
  let loading = true;
  let errorMsg = "";

  const API_URL = "http://localhost:8000";

  async function fetchMaterials() {
    loading = true;
    try {
      const res = await fetch(`${API_URL}/materials`);
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
</script>

<div class="p-8 max-w-7xl mx-auto space-y-6">
  <div class="flex justify-between items-center">
    <h1
      class="text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight"
    >
      Material Overview
    </h1>
  </div>

  {#if errorMsg}
    <Alert color="red" class="mb-4 shadow-sm">{errorMsg}</Alert>
  {/if}

  <div class="shadow-xl rounded-xl border border-gray-100 overflow-hidden">
    <Table hoverable={true} class="w-full text-left">
      <TableHead
        class="bg-gray-50 text-gray-700 uppercase tracking-wider text-sm"
      >
        <TableHeadCell>Material No.</TableHeadCell>
        <TableHeadCell>Short Text</TableHeadCell>
        <TableHeadCell>PO Text</TableHeadCell>
      </TableHead>
      <TableBody class="divide-y">
        {#if loading}
          <TableBodyRow>
            <TableBodyCell
              colspan={3}
              class="text-center py-8 text-gray-500 font-medium"
              >Loading data...</TableBodyCell
            >
          </TableBodyRow>
        {:else if materials.length === 0}
          <TableBodyRow>
            <TableBodyCell
              colspan={3}
              class="text-center py-8 text-gray-500 font-medium"
              >No unmatched materials found.</TableBodyCell
            >
          </TableBodyRow>
        {:else}
          {#each materials as item}
            <TableBodyRow class="hover:bg-blue-50/50 transition duration-150">
              <TableBodyCell class="font-semibold text-gray-900"
                >{item.material_number}</TableBodyCell
              >
              <TableBodyCell class="text-gray-600"
                >{item.short_text}</TableBodyCell
              >
              <TableBodyCell
                class="text-gray-500 text-sm max-w-xs truncate"
                title={item.purchase_order_text}
              >
                {item.purchase_order_text}
              </TableBodyCell>
            </TableBodyRow>
          {/each}
        {/if}
      </TableBody>
    </Table>
  </div>
</div>
