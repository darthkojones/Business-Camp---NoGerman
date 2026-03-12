<script lang="ts">
  import { goto } from "$app/navigation";
  export let currentStep = 1;

  const steps = [
    { number: 1, label: "Dateien hochladen", path: "/" },
    { number: 2, label: "Zuordnung prüfen", path: "/results" },
    { number: 3, label: "Übersicht & Export", path: "/overview" },
  ];

  function go(path: string) {
    goto(path);
  }
</script>

<nav class="flex items-center justify-center space-x-4 mb-10">
  {#each steps as step, idx}
    <button
      class="flex items-center space-x-2 text-sm font-medium focus:outline-none disabled:opacity-50"
      class:text-[#BB1E38]={currentStep === step.number}
      class:text-gray-500={currentStep !== step.number}
      disabled={currentStep < step.number}
      on:click={() => currentStep >= step.number && go(step.path)}
    >
      <span
        class="w-6 h-6 flex items-center justify-center rounded-full border"
        class:border-[#BB1E38]={currentStep === step.number}
        class:bg-[#BB1E38]={currentStep === step.number}
        class:text-white={currentStep === step.number}
        class:border-gray-300={currentStep !== step.number}
        class:text-gray-700={currentStep !== step.number}
      >
        {step.number}
      </span>
      <span>{step.label}</span>
    </button>

    {#if idx < steps.length - 1}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-4 w-4 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9 5l7 7-7 7"
        />
      </svg>
    {/if}
  {/each}
</nav>
