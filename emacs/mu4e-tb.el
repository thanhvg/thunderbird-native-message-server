(defun mu4e/thunderbird-mark-as-read (msg)
  "To set as `mu4e-view-auto-mark-as-read'"
  (message (format "http://localhost:1337/mid/%s" (mu4e-message-field msg :message-id)))
  (url-retrieve
   (format "http://localhost:1337/mid/%s" (mu4e-message-field msg :message-id))
   (lambda (_status) (kill-buffer (current-buffer)))
   nil
   nil)
  t)

(setq mu4e-view-auto-mark-as-read #'mu4e/thunderbird-mark-as-read)



;; (defun mu4e/collect-unread-message-ids (msglst)
;;   "Collect the first 10 unread message-ids from MSGLST."
;;   (let ((unread-ids '())
;;         (count 0))
;;     (dolist (msg msglst)
;;       (when (and (<= count 9)
;;                  (member 'unread (mu4e-message-field msg :flags)))
;;         (push (mu4e-message-field msg :message-id) unread-ids)
;;         (setq count (1+ count))))
;;     (nreverse unread-ids)))

(defun mu4e/collect-unread-message-ids (msglst)
  "Collect the first 10 unread message-ids from MSGLST."
  (let ((unread-ids '())
        (count 0))
    (cl-dolist (msg msglst)
      (when (>= count 100)
        (cl-return)) ; Exit dolist early

      (when (member 'unread (plist-get msg :flags))
        (push (plist-get msg :message-id) unread-ids)
        (setq count (1+ count))))
    (nreverse unread-ids)))


(defun mu4e/query-read-status (mids)
  (request "http://localhost:1337/query-read-status"
    :type "POST"
    :data (json-serialize `(:messages ,(vconcat mids)))
    :headers '(("Content-Type" . "application/json"))
    :parser (lambda ()
              (json-parse-buffer :object-type 'alist
                                  :null-object nil
                                  :false-object nil))
    :success (cl-function

              (lambda (&key data &allow-other-keys)
                (dolist (message-by-status (alist-get 'payload data))
                  (when (cdr message-by-status)
                    ;; (message (cmessage-by-status))
                    (mu4e--server-move (symbol-name (car message-by-status)) nil "+S-u-N")))))))


(defun mu4e/thunderbird-headers-append-func (msglst)
  (mu4e~headers-append-handler msglst)

  (mu4e/query-read-status (mu4e/collect-unread-message-ids msglst)))

(setq mu4e-headers-append-func #'mu4e/thunderbird-headers-append-func)

;; (json-serialize `(:messages ,(vconcat 1 2)))

;; (json-serialize (list :messages (vector "fpp")))

;; (json-serialize (list :id 42 :message ["hello world"]))
;; (json-serialize (list :id 42 :message ["hello world"]))

;; (vector '(1 2))

(defun mu4/thunderbird-mu4e-mark-execute-pre-hook (mark msg)
  (when (equal mark 'read)
    (mu4e/thunderbird-mark-as-read msg)))


(setq mu4e-mark-execute-pre-hook #'mu4/thunderbird-mu4e-mark-execute-pre-hook)
