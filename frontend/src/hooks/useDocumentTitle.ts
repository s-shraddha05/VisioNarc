import { useEffect } from "react";
import { APP_NAME } from "@/lib/brand";

export function useDocumentTitle(page: string) {
  useEffect(() => {
    document.title = `${page} · ${APP_NAME}`;
  }, [page]);
}
