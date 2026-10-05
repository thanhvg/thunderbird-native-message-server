;;; mu4e-tb.el --- mu4e <-> Thunderbird bridge  -*- lexical-binding: t; -*-
(require 'json)
(require 'url)
(require 'cl-lib)
(require 'seq)
(require 'mu4e)

;;;; transport ---------------------------------------------------------

(defun mu4e-tb--conn ()
  "Read port/token written by the Thunderbird extension."
  (let ((file (expand-file-name "mu4e-bridge/connection.json"
                                (or (getenv "XDG_RUNTIME_DIR")
                                    temporary-file-directory))))
    (unless (file-readable-p file)
      (user-error "Thunderbird bridge not running (no %s)" file))
    (json-read-file file)))

(defun mu4e-tb--finish ()
  "Parse the JSON body in the current response buffer, then kill it."
  (goto-char (point-min))
  (re-search-forward "\r?\n\r?\n")
  (let ((res (json-parse-buffer :object-type 'alist)))
    (kill-buffer (current-buffer))
    (when (alist-get 'error res)
      (error "Thunderbird bridge: %s" (alist-get 'error res)))
    res))

(defun mu4e-tb--request (path data &optional callback)
  "POST DATA (a plist) to PATH.  Async with CALLBACK, else return the reply."
  (let* ((conn (mu4e-tb--conn))
         (url (format "http://127.0.0.1:%d%s" (alist-get 'port conn) path))
         (url-request-method "POST")
         (url-request-extra-headers
          `(("Content-Type" . "application/json")
            ("Authorization" . ,(concat "Bearer " (alist-get 'token conn)))))
         (url-request-data (encode-coding-string (json-serialize data) 'utf-8)))
    (if callback
        (url-retrieve url
                      (lambda (status cb)
                        (if (plist-get status :error)
                            (message "Thunderbird bridge: %S" (plist-get status :error))
                          (funcall cb (mu4e-tb--finish))))
                      (list callback) t t)
      (with-current-buffer (url-retrieve-synchronously url t t 30)
        (mu4e-tb--finish)))))

;;;; mu4e -> Thunderbird: flags ------------------------------------------

(defun mu4e-tb--mark-hook (mark msg)
  (when-let ((flags (pcase mark
                      ('read   '(:read t))
                      ('unread '(:read :false))
                      ('flag   '(:flagged t))
                      ('unflag '(:flagged :false)))))
    (mu4e-tb--request
     "/set-flags"
     `(:items [(:mid ,(mu4e-message-field msg :message-id) ,@flags)])
     #'ignore)))

(add-hook 'mu4e-mark-execute-pre-hook #'mu4e-tb--mark-hook)

(setq mu4e-view-auto-mark-as-read
      (lambda (msg) (mu4e-tb--mark-hook 'read msg) t))

;;;; Thunderbird -> mu4e: read state on header listing -------------------

(defun mu4e-tb--refresh-read-status (msglst)
  (let ((mids (seq-take
               (cl-loop for m in msglst
                        when (memq 'unread (plist-get m :flags))
                        collect (plist-get m :message-id))
               100)))
    (when mids
      (mu4e-tb--request
       "/read-status" `(:mids ,(vconcat mids))
       (lambda (res)
         (dolist (kv res)
           (when (eq (alist-get 'read (cdr kv)) t)
             (mu4e--server-move (symbol-name (car kv)) nil "+S-u-N"))))))))

(setq mu4e-headers-append-func
      (lambda (msglst)
        (mu4e~headers-append-handler msglst)
        (mu4e-tb--refresh-read-status msglst)))

;;;; sending: hand the finished MIME message to a Thunderbird compose window

(defun mu4e-tb-send-via-compose ()
  (let ((res (mu4e-tb--request
              "/compose"
              `(:from ,(cadr (mail-extract-address-components
                              (message-fetch-field "from")))
                :eml ,(buffer-substring-no-properties (point-min) (point-max))))))
    (unless (eq (alist-get 'ok res) t)
      (error "Thunderbird compose failed"))))

(setq message-send-mail-function #'mu4e-tb-send-via-compose
      mu4e-sent-messages-behavior 'delete) ; Thunderbird files its own Sent copy

(provide 'mu4e-tb)
