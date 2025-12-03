package org.pytorch.demo.objectdetection;

import android.graphics.Rect;
import android.util.Log;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;

class Result {
    int classIndex;
    Float score;
    Rect rect;

    public Result(int cls, Float output, Rect rect) {
        this.classIndex = cls;
        this.score = output;
        this.rect = rect;
    }
}

public class PrePostProcessor {

    // 입력 크기(리사이즈용) — 일반적으로 320 또는 640
    public static int mInputWidth  = 320;
    public static int mInputHeight = 320;

    // 전처리: YOLOv5는 보통 mean/std 불필요
    public static final float[] NO_MEAN_RGB = new float[]{0f, 0f, 0f};
    public static final float[] NO_STD_RGB  = new float[]{1f, 1f, 1f};

    // 라벨
    static String[] mClasses = new String[]{"0","1","2","3"};

    // ★ CHANGED: 임계값/탐지 개수 (여러 개 박스 보장)
    private static final float SCORE_THRESH = 0.25f; // 약간 낮춰 여러 개 나오게
    private static final int   MAX_DETECTIONS = 100; // 충분히 크게
    private static final float NMS_IOU = 0.45f;

    // ★ CHANGED: 항상 "여러 개"를 유지 (true면 1개만)
    private static final boolean TOP1_ONLY = false;

    // 세터
    public static void setClasses(String[] classes) {
        if (classes != null && classes.length > 0) mClasses = classes;
    }
    public static void setInputSize(int w, int h) {
        if (w > 0 && h > 0) { mInputWidth = w; mInputHeight = h; }
    }

    // 편의 getter (로깅용)
    public static int getNumClasses() { return mClasses.length; }
    public static int getOutputRow() { return -1; }         // 동적 계산
    public static int getOutputColumn() { return -1; }      // 동적 계산
    public static int getExpectedOutputLength() { return -1; }

    // ─────────────────────────────────────────────────────────────────────
    // ★ CHANGED: 동적 후처리 — 두 가지 포맷을 자동 인식
    // 1) rows x (5 + N): [cx,cy,w,h,obj, p1..pN]
    // 2) rows x 6      : [cx,cy,w,h,conf, clsId]
    // ─────────────────────────────────────────────────────────────────────
    public static ArrayList<Result> postprocessDynamic(
            float[] outputs,
            float imgScaleX, float imgScaleY,
            float ivScaleX, float ivScaleY,
            float startX, float startY) {

        if (outputs == null || outputs.length == 0) {
            Log.e("OD", "outputs is empty");
            return null;
        }

        int N = mClasses.length;

        // (5+N) 형식 시도
        int colsA = 5 + N;
        if (outputs.length % colsA == 0) {
            int rows = outputs.length / colsA;
            Log.d("OD", "Detected format: (5+N) cols=" + colsA + ", rows=" + rows);
            return parseFormat5plusN(outputs, rows, colsA, imgScaleX, imgScaleY, ivScaleX, ivScaleY, startX, startY);
        }

        // 6열 형식 시도
        int colsB = 6;
        if (outputs.length % colsB == 0) {
            int rows = outputs.length / colsB;
            Log.d("OD", "Detected format: 6-cols (conf+clsId). rows=" + rows);
            return parseFormat6(outputs, rows, imgScaleX, imgScaleY, ivScaleX, ivScaleY, startX, startY);
        }

        // 둘 다 아니면 해석 불가
        Log.e("OD", "Unknown output format. length=" + outputs.length + ", N=" + N);
        return null;
    }

    /** 포맷 A: [cx,cy,w,h,obj, p1..pN] */
    private static ArrayList<Result> parseFormat5plusN(
            float[] out, int rows, int cols,
            float imgScaleX, float imgScaleY,
            float ivScaleX, float ivScaleY,
            float startX, float startY) {

        ArrayList<Result> list = new ArrayList<>();
        int N = mClasses.length;

        for (int i = 0; i < rows; i++) {
            int base = i * cols;
            float obj = out[base + 4];
            if (obj < SCORE_THRESH) continue;

            float cx = out[base];
            float cy = out[base + 1];
            float w  = out[base + 2];
            float h  = out[base + 3];

            float left   = imgScaleX * (cx - w / 2f);
            float top    = imgScaleY * (cy - h / 2f);
            float right  = imgScaleX * (cx + w / 2f);
            float bottom = imgScaleY * (cy + h / 2f);

            // 최대 class 확률
            int cls = 0;
            float maxP = out[base + 5];
            for (int j = 1; j < N; j++) {
                float p = out[base + 5 + j];
                if (p > maxP) { maxP = p; cls = j; }
            }

            // 점수: obj * classProb → 더 안정적
            float score = obj * maxP;
            if (score < SCORE_THRESH) continue;

            Rect rect = new Rect(
                    (int) (startX + ivScaleX * left),
                    (int) (startY + ivScaleY * top),
                    (int) (startX + ivScaleX * right),
                    (int) (startY + ivScaleY * bottom));

            list.add(new Result(cls, score, rect));
        }

        // ★ CHANGED: NMS에서 상한/Top1 제어
        int limit = TOP1_ONLY ? 1 : MAX_DETECTIONS;
        return nonMaxSuppression(list, limit, NMS_IOU);
    }

    /** 포맷 B: [cx,cy,w,h,conf, clsId] */
    private static ArrayList<Result> parseFormat6(
            float[] out, int rows,
            float imgScaleX, float imgScaleY,
            float ivScaleX, float ivScaleY,
            float startX, float startY) {

        ArrayList<Result> list = new ArrayList<>();

        for (int i = 0; i < rows; i++) {
            int base = i * 6;
            float conf = out[base + 4];
            if (conf < SCORE_THRESH) continue;

            float cx = out[base];
            float cy = out[base + 1];
            float w  = out[base + 2];
            float h  = out[base + 3];

            int cls = Math.max(0, Math.min(mClasses.length - 1, Math.round(out[base + 5])));

            float left   = imgScaleX * (cx - w / 2f);
            float top    = imgScaleY * (cy - h / 2f);
            float right  = imgScaleX * (cx + w / 2f);
            float bottom = imgScaleY * (cy + h / 2f);

            Rect rect = new Rect(
                    (int) (startX + ivScaleX * left),
                    (int) (startY + ivScaleY * top),
                    (int) (startX + ivScaleX * right),
                    (int) (startY + ivScaleY * bottom));

            list.add(new Result(cls, conf, rect));
        }

        // ★ CHANGED: NMS에서 상한/Top1 제어
        int limit = TOP1_ONLY ? 1 : MAX_DETECTIONS;
        return nonMaxSuppression(list, limit, NMS_IOU);
    }

    /** NMS */
    static ArrayList<Result> nonMaxSuppression(ArrayList<Result> boxes, int limit, float iouThreshold) {
        if (boxes.isEmpty()) return boxes;

        // 점수 내림차순
        Collections.sort(boxes, new Comparator<Result>() {
            @Override public int compare(Result a, Result b) { return b.score.compareTo(a.score); }
        });

        ArrayList<Result> selected = new ArrayList<>();
        boolean[] active = new boolean[boxes.size()];
        Arrays.fill(active, true);
        int numActive = active.length;

        for (int i = 0; i < boxes.size(); i++) {
            if (!active[i]) continue;
            Result A = boxes.get(i);
            selected.add(A);
            if (selected.size() >= limit) break; // ★ CHANGED: limit 반영

            for (int j = i + 1; j < boxes.size(); j++) {
                if (!active[j]) continue;
                Result B = boxes.get(j);
                if (IOU(A.rect, B.rect) > iouThreshold) {
                    active[j] = false; numActive--;
                    if (numActive <= 0) break;
                }
            }
            if (numActive <= 0) break;
        }
        return selected;
    }

    static float IOU(Rect a, Rect b) {
        float w = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        float h = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        float inter = w * h;
        float areaA = Math.max(0, a.right - a.left) * Math.max(0, a.bottom - a.top);
        float areaB = Math.max(0, b.right - b.left) * Math.max(0, b.bottom - b.top);
        return inter / (areaA + areaB - inter + 1e-6f);
    }

    // ─────────────────────────────────────────────────────────────────────
    // (참고) 옛 코드와의 호환이 필요하면 아래 래퍼를 남겨둘 수 있어요.
    // 하지만 지금 프로젝트에선 ObjectDetectionActivity가 postprocessDynamic을
    // 사용하므로 필요 없습니다. 주석만 남깁니다.
    //
    // public static ArrayList<Result> outputsToNMSPredictions(...) { ... }
    // ─────────────────────────────────────────────────────────────────────
}
