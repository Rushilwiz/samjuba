<script lang="ts">
  import { uploads } from "$lib/uploads.svelte";

  let fileInput: HTMLInputElement;

  function openPicker() {
    fileInput.click();
  }

  function handleChange(e: Event) {
    const target = e.currentTarget as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      uploads.addFiles(target.files);
    }
    target.value = "";
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    if (bytes < 1024 * 1024 * 1024)
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
  }
</script>

<svelte:head>
  <title>In memory of Samjuben Shamjibhai Vaghani</title>
</svelte:head>

<main class="flex min-h-[100dvh] flex-col items-center px-6 py-14 sm:py-20">
  <div class="flex w-full max-w-[480px] flex-col items-center">
    <header class="mb-10 text-center">
      <h1 class="font-gujarati mb-3 text-3xl leading-[1.1] sm:text-6xl">
        સમજુબેન શામજીભાઈ વાઘાણી
      </h1>
      <p
        class="font-script lowercase text-4xl leading-tight text-neutral-700 sm:text-5xl"
      >
        Samjuben Shamjibhai Vaghani
      </p>
    </header>

    <p
      class="font-sans mb-10 text-center text-base leading-relaxed text-neutral-600"
    >
      Share your photos and videos in her memory.<br />
      Tap below to choose from your phone.
    </p>

    <input
      bind:this={fileInput}
      type="file"
      accept="image/*,video/*"
      multiple
      onchange={handleChange}
      class="hidden"
    />

    <button
      type="button"
      onclick={openPicker}
      class="font-sans w-full max-w-xs rounded-full bg-neutral-900 px-8 py-5 text-lg font-medium text-white shadow-sm transition-transform active:scale-[0.98]"
    >
      Upload photos &amp; videos
    </button>

    {#if uploads.items.length > 0}
      <ul class="font-sans mt-12 w-full space-y-3">
        {#each uploads.items as item (item.id)}
          <li class="rounded-lg border border-neutral-200 bg-white p-4">
            <div class="flex items-baseline justify-between gap-3 text-sm">
              <span class="flex-1 truncate text-neutral-800"
                >{item.file.name}</span
              >
              <span class="shrink-0 text-xs text-neutral-500"
                >{formatSize(item.file.size)}</span
              >
            </div>
            <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-neutral-100">
              <div
                class="h-full transition-[width] duration-200"
                class:bg-neutral-900={item.status !== "failed"}
                class:bg-red-500={item.status === "failed"}
                style="width: {item.status === 'done'
                  ? 100
                  : Math.round(item.progress * 100)}%"
              ></div>
            </div>
            <div class="mt-2 flex items-center justify-between gap-3 text-xs">
              {#if item.status === "queued"}
                <span class="text-neutral-500">Waiting…</span>
              {:else if item.status === "uploading"}
                <span class="text-neutral-600">
                  Uploading {Math.round(item.progress * 100)}%
                </span>
              {:else if item.status === "done"}
                <span class="text-neutral-600">Added</span>
              {:else}
                <span class="flex-1 truncate text-red-600">
                  {item.error ?? "Upload failed"}
                </span>
                <button
                  type="button"
                  onclick={() => uploads.retry(item.id)}
                  class="shrink-0 text-neutral-900 underline underline-offset-2"
                >
                  Retry
                </button>
              {/if}
            </div>
          </li>
        {/each}
      </ul>

      {#if uploads.allDone}
        <p class="font-sans mt-10 text-center text-neutral-700">
          Thank you — your photos have been added.
        </p>
        <button
          type="button"
          onclick={() => uploads.clearDone()}
          class="font-sans mt-3 text-sm text-neutral-500 underline underline-offset-2"
        >
          Upload more
        </button>
      {/if}
    {/if}
  </div>
</main>
