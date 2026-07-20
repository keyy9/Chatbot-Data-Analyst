import { useEffect, type RefObject } from "react";

export const useAutoScroll = (ref: RefObject<HTMLElement | null>, dependency: any) => {
  useEffect(() => {
    if (ref.current) {
      ref.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [dependency, ref]);
};
