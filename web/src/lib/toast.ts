import { watch, type WatchSource } from "vue";
import { useToast } from "primevue/usetoast";

const TOAST_LIFE_MS = 4000;

export function useAppToast() {
  const toast = useToast();

  function showSuccess(detail: string, summary = "Success"): void {
    if (detail.trim() === "") {
      return;
    }

    toast.add({
      detail,
      life: TOAST_LIFE_MS,
      severity: "success",
      summary,
    });
  }

  function showError(detail: string, summary = "Error"): void {
    if (detail.trim() === "") {
      return;
    }

    toast.add({
      detail,
      life: TOAST_LIFE_MS,
      severity: "error",
      summary,
    });
  }

  return {
    showError,
    showSuccess,
  };
}

export function watchToastError(source: WatchSource<string>, summary = "Error"): void {
  const { showError } = useAppToast();

  watch(source, (message, previousMessage) => {
    if (message.trim() === "" || message === previousMessage) {
      return;
    }

    showError(message, summary);
  });
}
