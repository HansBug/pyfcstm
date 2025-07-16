/*
 * 檔案名稱: traditional_chinese_sample.c
 * 功能描述: 這是一個示範繁體中文註釋的C語言程式碼範例
 * 注意: 此程式碼僅用於編碼測試，不保證功能完整性
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 定義一些常數
#define 最大值 100
#define 緩衝區大小 256

// 結構體定義
typedef struct 學生資訊 {
    int 學號;
    char 姓名[50];
    float 成績;
} 學生;

/*
 * 函數: 計算平均分
 * 參數: 成績陣列和數量
 * 返回: 平均分數值
 * 說明: 這裡包含了一些繁體中文字符用於測試各種編碼
 */
float 計算平均分(float 分數[], int 數量) {
    float 總分 = 0.0;
    int i;

    // 遍歷所有分數並累加
    for (i = 0; i < 數量; i++) {
        總分 += 分數[i];  // 累加每個學生的分數
    }

    // 返回平均值，注意處理除零情況
    return 數量 > 0 ? 總分 / 數量 : 0;
}

/**
 * 主函數 - 程式進入點
 * 包含多種繁體中文字符和符號：【】、；：''""，。？！（）
 */
int main() {
    // 宣告變數
    int i, 學生數量 = 3;
    float 所有分數[最大值];
    char 臨時緩衝區[緩衝區大小];
    學生 班級[10];  // 班級學生陣列

    printf("這是一個測試程式，包含繁體中文註釋和變數名\n");

    /* 初始化學生資訊 */
    班級[0].學號 = 1001;
    strcpy(班級[0].姓名, "張三");  // 複製姓名
    班級[0].成績 = 85.5;

    班級[1].學號 = 1002;
    strcpy(班級[1].姓名, "李四");  // 另一個學生
    班級[1].成績 = 92.0;

    班級[2].學號 = 1003;
    strcpy(班級[2].姓名, "王五");  // 第三個學生
    班級[2].成績 = 78.5;

    // 收集所有分數用於計算
    for (i = 0; i < 學生數量; i++) {
        所有分數[i] = 班級[i].成績;

        // 輸出每個學生的資訊
        printf("學號：%d，姓名：%s，成績：%.1f\n",
               班級[i].學號, 班級[i].姓名, 班級[i].成績);
    }

    // 計算並顯示平均分
    float 平均分 = 計算平均分(所有分數, 學生數量);
    printf("全班平均分是：%.2f\n", 平均分);

    /*
     * 以下是一些繁體中文標點符號測試：
     * 句號。問號？驚嘆號！逗號，頓號、冒號：分號；
     * 引號""''括號（）《》【】｛｝
     */

    // 特殊字元測試：珍珠奶茶、臺灣、香港、澳門
    char 特殊字串[] = "測試：珍珠奶茶、臺灣、香港、澳門";
    printf("%s\n", 特殊字串);

    // 包含Big5/CP950特有字符
    char 特殊字元[] = "測試：機械、漢字、臺灣、國際、鄉鎮、燈會";
    printf("%s\n", 特殊字元);

    return 0;  // 正常結束
}
