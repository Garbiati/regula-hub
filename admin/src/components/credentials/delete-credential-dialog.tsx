"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDeleteCredential } from "@/hooks/use-credential-mutations";
import type { Credential } from "@/types/credential";

interface DeleteCredentialDialogProps {
  open: boolean;
  onClose: () => void;
  credential: Credential;
}

export function DeleteCredentialDialog({ open, onClose, credential }: DeleteCredentialDialogProps) {
  const t = useTranslations();
  const deleteMutation = useDeleteCredential();

  const handleDelete = () => {
    deleteMutation.mutate(credential.id, { onSuccess: onClose });
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("credentials.delete_title")}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          {t("credentials.delete_confirm", { username: credential.username })}
        </p>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t("common.close")}</Button>
          <Button variant="destructive" onClick={handleDelete} disabled={deleteMutation.isPending}>
            {t("credentials.delete_action")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
