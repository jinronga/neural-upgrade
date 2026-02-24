import { useEffect } from "react";

export const useWindowTitle = (title: string) => {
  useEffect(() => {
    const prev = document.title;
    document.title = title;
    return () => {
      document.title = prev;
    };
  }, [title]);
};

